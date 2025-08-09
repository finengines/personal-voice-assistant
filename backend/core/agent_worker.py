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
logger = logging.getLogger("agent-worker")


def _get_env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = os.getenv(name)
    return val if val is not None and str(val).strip() != "" else default


def _build_mcp_servers() -> List[mcp.MCPServer]:
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

    # Optionally add additional servers via JSON file if present
    # cfg_path = "/app/config/mcp_servers.json"
    # try:
    #     if os.path.exists(cfg_path):
    #         import json
    #
    #         with open(cfg_path, "r") as f:
    #             cfg = json.load(f)
    #         for sid, s in (cfg.get("servers", {}) or {}).items():
    #             if not s.get("enabled", False):
    #                 continue
    #             url = s.get("url")
    #             if not url:
    #                 continue
    #             headers: Dict[str, str] = {}
    #             auth = s.get("auth") or {}
    #             if auth.get("type") == "bearer" and auth.get("token"):
    #                 headers["Authorization"] = f"Bearer {auth['token']}"
    #             try:
    #                 servers.append(
    #                     mcp.MCPServerHTTP(
    #                         url=url,
    #                         headers=headers or None,
    #                         timeout=float(s.get("timeout", 15.0)),
    #                         sse_read_timeout=float(s.get("sse_read_timeout", 90.0)),
    #                     )
    #                 )
    #                 logger.info("Added MCP server %s: %s", sid, url)
    #             except Exception as e:
    #                 logger.warning("Failed to create MCP server '%s': %s", sid, e)
    # except Exception as e:
    #     logger.warning("MCP JSON config load failed: %s", e)

    logger.info("Total MCP servers configured: %d", len(servers))
    return servers


class MinimalAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are a helpful voice assistant. Keep replies concise.")

    async def on_enter(self):
        # Don't auto-greet; wait for user. Keep consistent with UI behavior.
        pass

    @function_tool
    async def get_current_year(self) -> str:
        import datetime as _dt

        return str(_dt.datetime.utcnow().year)

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
    # Attach room in logs
    ctx.log_context_fields = {"room": ctx.room.name}

    # Build core components
    vad = silero.VAD.load()
    stt = deepgram.STT(model="nova-3", language="multi")
    llm = openai.LLM(model="gpt-4o-mini")
    tts = openai.TTS(voice="ash")

    # Optional MCP servers
    mcp_servers = _build_mcp_servers() or None

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

    # Forward tool execution events to the frontend (if available in current SDK)
    @session.on("function_tools_executed")
    def _on_tools_executed(ev):  # pragma: no cover
        try:
            agent = session.agent
            for fnc_call in getattr(ev, "function_calls", []) or []:
                name = getattr(fnc_call, "name", "tool")
                if hasattr(agent, "emit_tool"):
                    agent.emit_tool(name)
        except Exception as e:
            logger.warning("tool event forward failed: %s", e)

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
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

    # Normal run
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


