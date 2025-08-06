import logging
import asyncio
import json
from typing import List, Optional
from datetime import datetime, timezone
import pytz

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    mcp,
    metrics,
)
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero, noise_cancellation

# Conditional import for turn detection
try:
    from livekit.plugins.turn_detector.multilingual import MultilingualModel
    MULTILINGUAL_AVAILABLE = True
except ImportError:
    MULTILINGUAL_AVAILABLE = False
    MultilingualModel = None

# GraphitiAgent integration is now handled via MCP in DynamicAgent

logger = logging.getLogger("simple-agent")

load_dotenv()


# Note: MCP server loading and SimpleAgent class removed - now using DynamicAgent with preset-based configuration


async def entrypoint(ctx: JobContext):
    # Each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # ------------------------------------------------------------------
    # 1. Load agent preset for this room
    # ------------------------------------------------------------------
    from core.dynamic_agent import (
        get_preset_for_room,
        load_mcp_servers_for_preset,
        create_tts_from_config,
        create_llm_from_config,
        create_stt_from_config,
        SpeedConfig,
    )

    logger.info("🔄 Loading preset configuration for room '%s'…", ctx.room.name)
    preset = await get_preset_for_room(ctx)
    logger.info("✅ Using preset '%s'", preset.name)

    # ------------------------------------------------------------------
    # 2. Build components based on preset
    # ------------------------------------------------------------------
    tts = await create_tts_from_config(preset.voice_config)
    llm = await create_llm_from_config(preset.llm_config)
    stt = create_stt_from_config(preset.stt_config)

    speed = preset.agent_config.speed_config or SpeedConfig()

    # ------------------------------------------------------------------
    # 3. Load MCP servers
    # ------------------------------------------------------------------
    mcp_servers = await load_mcp_servers_for_preset(preset.mcp_server_ids)
    if mcp_servers:
        logger.info("✅ Loaded %s MCP server(s)", len(mcp_servers))
    else:
        logger.info("ℹ️  No external MCP servers configured")

    # Temporarily force VAD to avoid turn detector model issues
    turn_detection_impl = "vad"
    # turn_detection_impl = (
    #     MultilingualModel() if (speed.advanced_turn_detection and MULTILINGUAL_AVAILABLE and MultilingualModel) else "vad"
    # )

    # ------------------------------------------------------------------
    # 4. Create AgentSession
    # ------------------------------------------------------------------
    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        llm=llm,
        stt=stt,
        tts=tts,
        turn_detection=turn_detection_impl,
        mcp_servers=mcp_servers or None,
        allow_interruptions=preset.agent_config.allow_interruptions,
        preemptive_generation=preset.agent_config.preemptive_generation,
        min_interruption_duration=speed.min_interruption_duration,
        min_endpointing_delay=speed.min_endpointing_delay,
        max_endpointing_delay=speed.max_endpointing_delay,
        max_tool_steps=preset.agent_config.max_tool_steps,
    )

    # Log metrics as they are emitted
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"📊 Usage: {summary}")

    # Shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)
    
    # Create the agent using the preset configuration
    from core.dynamic_agent import DynamicAgent
    agent = DynamicAgent(preset, ctx_room=ctx.room)

    # CRITICAL: Connect to the room context BEFORE starting the session
    logger.info("🔌 Connecting to room context...")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("✅ Room context connected")

    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Background voice cancellation removes background noise and extra speakers
            # This significantly improves voice activity detection and turn detection
            noise_cancellation=noise_cancellation.BVC(),
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True, audio_enabled=True),
    )


def prewarm(proc: JobProcess):
    """
    This function is called before the worker starts processing jobs.
    Use this to download any models or assets that are needed for the agent.
    """
    # Configure VAD with optimized settings for better speech detection
    proc.userdata["vad"] = silero.VAD.load(
        # Minimum speech duration to consider as actual speech (prevents noise triggering)
        min_speech_duration=0.2,
        # Minimum silence duration before considering speech ended
        min_silence_duration=0.5,
        # Speech probability threshold (0.5 = balanced, higher = more strict)
        activation_threshold=0.5,
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm)) 