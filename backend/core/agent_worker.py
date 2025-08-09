#!/usr/bin/env python3
"""
Minimal, robust single-agent worker aligned with LiveKit examples.
Keeps tool/MCP integration simple and reliable, and emits frontend UI events.
"""

import logging
import os
from collections.abc import AsyncIterable
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    ModelSettings,
    WorkerOptions,
    cli,
    mcp,
    metrics,
)
from livekit.agents.llm import function_tool
from livekit.agents.llm.chat_context import ChatContext, ChatMessage
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero

load_dotenv()

# Ensure logging is visible in container logs
_root = logging.getLogger()
if not _root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    )
else:
    _root.setLevel(logging.INFO)

logger = logging.getLogger("agent-worker")


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val is not None and str(val).strip() != "" else default


async def _fetch_enabled_servers_from_api() -> Dict[str, Any]:
    """Fetch MCP servers from the internal MCP API if available.

    Returns a dict keyed by server_id with entries including url, server_type, enabled, and auth.
    """
    import aiohttp

    base_url = _get_env("MCP_API_BASE", "http://localhost:8082")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/servers") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        servers = {}
                        for s in data.get("data", []):
                            servers[s["server_id"]] = {
                                "name": s.get("name"),
                                "server_type": s.get("server_type"),
                                "url": s.get("url"),
                                "enabled": s.get("enabled", False),
                                "auth": s.get("auth") or {},
                            }
                        return servers
    except Exception as e:
        logger.info("MCP API not available for servers: %s", e)
    return {}


async def _build_mcp_servers() -> List[mcp.MCPServer]:
    """Build a minimal list of MCPServerHTTP from env/DB/API when available.

    Supports:
    - GRAPHITI_MCP_URL (optional)
    - Future: extend to pull from local MCP API/db if needed
    """
    servers: List[mcp.MCPServer] = []

    graphiti_url = _get_env("GRAPHITI_MCP_URL", "").strip()
    if graphiti_url:
        try:
            servers.append(
                mcp.MCPServerHTTP(
                    url=graphiti_url,
                    timeout=10.0,
                    sse_read_timeout=60.0,
                )
            )
            logger.info("Added Graphiti MCP server: %s", graphiti_url)
        except Exception as e:
            logger.warning("Failed to add Graphiti MCP server: %s", e)

    # Query internal MCP API for enabled servers to attach
    try:
        api_servers = await _fetch_enabled_servers_from_api()
        for sid, cfg in api_servers.items():
            if not cfg.get("enabled"):
                continue
            if cfg.get("server_type") not in ("sse", "http"):
                continue
            url = (cfg.get("url") or "").strip()
            if not url:
                continue
            headers: Dict[str, str] = {}
            auth = cfg.get("auth") or {}
            if auth.get("type") == "bearer" and auth.get("token"):
                headers["Authorization"] = f"Bearer {auth['token']}"
            elif auth.get("type") == "api_key" and auth.get("token"):
                headers["X-API-Key"] = auth["token"]
            try:
                servers.append(
                    mcp.MCPServerHTTP(
                        url=url,
                        headers=headers or None,
                        timeout=15.0,
                        sse_read_timeout=90.0,
                    )
                )
                logger.info("Added MCP server from API %s: %s", sid, url)
            except Exception as e:
                logger.warning("Failed to create MCP server '%s': %s", sid, e)
    except Exception as e:
        logger.info("MCP API servers unavailable: %s", e)

    logger.info("Total MCP servers configured: %d", len(servers))
    return servers


class MinimalAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. Keep replies concise. "
                "Use available tools when they help answer the user's question. "
                "You can also call external MCP tools when appropriate."
            )
        )

    async def on_enter(self):
        # Don't auto-greet; wait for user. Keep consistent with UI behavior.
        pass

    @function_tool
    async def get_current_year(self) -> str:
        import datetime as _dt

        return str(_dt.datetime.utcnow().year)

    @function_tool
    async def echo(self, text: str) -> str:
        """Echo back the provided text (for tool-call verification)."""
        return text

    def _publish_event(self, payload: Dict[str, Any]) -> None:
        try:
            room = getattr(self.session, "room", None)
            if room and room.isconnected():
                import json, asyncio as _aio

                async def _do():
                    try:
                        await room.local_participant.publish_data(
                            json.dumps(payload).encode(), reliable=True
                        )
                    except Exception as e:  # pragma: no cover
                        logger.warning("Failed to publish event: %s", e)

                _aio.create_task(_do())
        except Exception as e:
            logger.debug("publish_event error: %s", e)

    def emit_memory(self, etype: str, message: str = "") -> None:
        self._publish_event({"type": etype, "message": message})

    def emit_tool(self, name: str) -> None:
        self._publish_event({"type": "tool-called", "tool": name})

    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage):
        # Example memory event for the UI indicator
        self.emit_memory("memory-searching", "Processing input")


async def entrypoint(ctx: JobContext):
    logger.info("entrypoint invoked for room placeholder (job will provide actual room)")
    # Attach room in logs
    ctx.log_context_fields = {"room": ctx.room.name}

    # Build core components
    vad = silero.VAD.load()
    stt = deepgram.STT(model="nova-3", language="multi")
    llm = openai.LLM(model="gpt-4o-mini")
    tts = openai.TTS(voice="ash")

    # Optional MCP servers
    logger.info("loading MCP servers…")
    mcp_servers = await _build_mcp_servers() or None
    logger.info("MCP servers loaded: %d", len(mcp_servers) if mcp_servers else 0)

    session = AgentSession(
        vad=vad,
        stt=stt,
        llm=llm,
        tts=tts,
        turn_detection="vad",
        mcp_servers=mcp_servers,
        allow_interruptions=True,
        min_endpointing_delay=0.5,
        max_endpointing_delay=5.0,
    )

    usage = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage.collect(ev.metrics)

    @session.on("agent_state_changed")
    def _on_state(ev):  # pragma: no cover
        logger.info("agent_state_changed: %s", getattr(ev, "new_state", "unknown"))

    # Forward tool execution events to the frontend (if available in current SDK)
    @session.on("function_tools_executed")
    def _on_tools_executed(ev):  # pragma: no cover
        try:
            agent = session.agent
            for fnc_call in getattr(ev, "function_calls", []) or []:
                name = getattr(fnc_call, "name", "tool")
                logger.info("tool executed: %s", name)
                if hasattr(agent, "emit_tool"):
                    agent.emit_tool(name)
        except Exception as e:
            logger.warning("tool event forward failed: %s", e)

    logger.info("connecting to LiveKit room context…")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("room context connected, starting session…")
    agent = MinimalAgent()
    await session.start(agent=agent, room=ctx.room)

    # Emit a startup memory event for UI sanity check
    agent.emit_memory("memory-startup", "Agent initialized")


if __name__ == "__main__":
    # Support model pre-download for Docker builds (optional)
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        try:
            # Trigger VAD model download
            silero.VAD.load()
            print("✅ VAD model downloaded")
        except Exception as e:
            print(f"❌ Model download failed: {e}")
            sys.exit(1)
        sys.exit(0)

    # Normal run (bind worker health server to 8085 to avoid clashes and match healthcheck)
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, port=8085))


