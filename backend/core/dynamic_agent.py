#!/usr/bin/env python3
"""
Dynamic Agent Implementation

This module provides a dynamic agent that can load different presets
and configure itself with different system prompts, voices, and MCP servers.
Enhanced with intelligent memory capabilities from Graphiti.

CONSOLIDATED FUNCTIONALITY:
- Merged all memory functionality from GraphitiAgent (removed)
- Includes speed optimizations from SpeedOptimizedAgent (removed)
- Unified single agent architecture for all use cases
"""

import logging
import asyncio
import json
import os
import re
import time
import requests
import numpy as np
from collections.abc import AsyncIterable
from typing import List, Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    mcp,
    metrics,
    utils,
    ModelSettings,
    AutoSubscribe,
)
from livekit import rtc
from livekit.agents.llm import function_tool, ChatContext, ChatMessage
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import deepgram, openai, silero, cartesia, elevenlabs

# Audio processing optimization
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    # logger not defined yet, use print instead
    print("librosa not available - audio speedup optimization disabled")

try:
    from livekit.plugins import noise_cancellation
except ImportError:
    noise_cancellation = None

# Disable multilingual turn detector to avoid model loading issues
MULTILINGUAL_AVAILABLE = False
MultilingualModel = None
# # Conditional import for turn detection
# try:
#     from livekit.plugins.turn_detector.multilingual import MultilingualModel
#     MULTILINGUAL_AVAILABLE = True
# except ImportError:
#     MULTILINGUAL_AVAILABLE = False
#     MultilingualModel = None

from api.preset_manager import preset_manager
from agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig, SpeedConfig
from core.api_key_manager import api_key_manager
from database import init_db

logger = logging.getLogger("dynamic-agent")

# Ensure env vars from .env are available when running locally
load_dotenv()

# MCP client for Graphiti integration will be available through the session
GRAPHITI_AVAILABLE = True  # Will be set based on MCP server availability

# Toggle to completely disable internal/REST-based memory system and rely solely on MCP tools
INTERNAL_MEMORY_ENABLED = False


class DynamicAgent(Agent):
    """Agent that configures itself based on a preset and includes built-in tools with enhanced memory capabilities"""
    
    # Graphiti API configuration
    # Prefer explicit MCP URL; if missing but API URL is provided, derive MCP as <API>/sse
    GRAPHITI_MCP_URL = os.getenv("GRAPHITI_MCP_URL", "").strip()
    GRAPHITI_API_URL = os.getenv("GRAPHITI_API_URL", "").strip()

    # Derive MCP URL from API URL when only API is configured
    if (
        (not GRAPHITI_MCP_URL or "your-graphiti-instance.com" in GRAPHITI_MCP_URL)
        and GRAPHITI_API_URL
        and "your-graphiti-instance.com" not in GRAPHITI_API_URL
    ):
        GRAPHITI_MCP_URL = GRAPHITI_API_URL.rstrip("/") + "/sse"

    @staticmethod
    def _is_placeholder_graphiti_url(url: Optional[str]) -> bool:
        try:
            return (not url) or ("your-graphiti-instance.com" in url)
        except Exception:
            return True
    
    def __init__(self, preset: AgentPresetConfig, ctx_room=None) -> None:
        # Store preset for async initialization
        self.preset = preset
        self.preset_id = preset.id
        self.preset_name = preset.name
        self.ctx_room = ctx_room
        
        # Initialize with basic prompt, will be enhanced in on_enter
        super().__init__(
            instructions=preset.system_prompt,
        )
        self.preset_id = preset.id
        self.preset_name = preset.name
        
        # Audio optimization settings
        speed_config = preset.agent_config.speed_config if preset.agent_config else None
        self.audio_speed_factor = getattr(speed_config, 'audio_speed_factor', 1.0) if speed_config else 1.0
        self.enable_audio_speedup = LIBROSA_AVAILABLE and self.audio_speed_factor != 1.0
        
        # Fast pre-response system settings
        self.enable_fast_preresponse = getattr(speed_config, 'fast_preresponse', False) if speed_config else False
        self._fast_llm = None
        self._fast_llm_prompt = None
        
        if self.enable_fast_preresponse:
            self._setup_fast_preresponse()
        
        # Memory system initialization (disabled in simplified mode; rely on MCP tools)
        self.memory_threshold = 3
        self.conversation_turns = 0
        self.conversation_start_time = None
        self.conversation_history = []
        self.memory_context = ""
        self.memory_api_available = False if not INTERNAL_MEMORY_ENABLED else not self._is_placeholder_graphiti_url(self.GRAPHITI_API_URL)
        self.local_memory = []
        
        # Memory performance tracking
        self.memory_stats = {
            'searches_performed': 0,
            'memories_retrieved': 0,
            'memories_stored': 0,
            'search_times': [],
            'retrieval_success_rate': 0.0,
            'last_search_time': None,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Memory optimization features
        self.memory_cache = {}  # Simple LRU-style cache
        self.cache_max_size = 100
        self.cache_ttl = 300  # 5 minutes
        self.memory_search_timeout = 1.5  # Aggressive timeout for low latency
        self.min_query_length = 3  # Skip memory search for very short queries
        self.skip_patterns = [  # Skip memory for these common patterns
            r'^(hi|hello|hey|ok|okay|yes|no|thanks|thank you)$',
            r'^(what|how|when|where|why|who)\s+(is|are|was|were)\s+(the|a|an)\s+\w+\?*$'  # Simple factual questions
        ]

    async def _combine_prompts(self, agent_prompt: str) -> str:
        """Combine global system prompt with agent-specific prompt"""
        try:
            from core.global_settings_manager import global_settings_manager
            global_prompt = await global_settings_manager.get_global_system_prompt()
            
            if global_prompt:
                # Combine global prompt with agent prompt
                combined = f"{global_prompt}\n\n{agent_prompt}"
                logger.info(f"✅ Combined global prompt ({len(global_prompt)} chars) with agent prompt ({len(agent_prompt)} chars)")
                return combined
            else:
                logger.info("ℹ️ No global prompt found, using agent prompt only")
                return agent_prompt
        except Exception as e:
            logger.warning(f"Failed to get global system prompt: {e}")
            return agent_prompt

    def _enhance_prompt_with_memory(self, original_prompt: str) -> str:
        """Enhance the system prompt with memory guidance"""
        memory_enhancement = """

Memory System Guidelines:
- You have access to relevant memories that are automatically provided as context
- Use these memories naturally in your responses - you don't need to mention checking memory  
- If someone asks for advice or recommendations, consider any relevant personal information you know about them
- Respond naturally and helpfully, incorporating your knowledge of the user seamlessly
- When you learn something important about the user, it will be automatically saved to memory"""
        
        return original_prompt + memory_enhancement

    def _should_skip_memory_search(self, user_input: str) -> bool:
        """Determine if we should skip memory search for performance"""
        # Skip very short queries
        if len(user_input.strip()) < self.min_query_length:
            return True
        
        # Skip common conversational patterns that don't need memory
        for pattern in self.skip_patterns:
            if re.search(pattern, user_input.strip(), re.IGNORECASE):
                return True
        
        return False

    def _get_cache_key(self, query: str) -> str:
        """Generate cache key for memory queries"""
        # Normalize the query for better cache hits
        normalized = re.sub(r'\s+', ' ', query.lower().strip())
        return f"memory:{normalized}"

    def _get_cached_memory(self, query: str) -> Optional[List[str]]:
        """Get cached memory results if available and valid"""
        cache_key = self._get_cache_key(query)
        
        if cache_key in self.memory_cache:
            cached_data = self.memory_cache[cache_key]
            # Check if cache entry is still valid (TTL)
            if time.time() - cached_data['timestamp'] < self.cache_ttl:
                self.memory_stats['cache_hits'] += 1
                logger.debug(f"[Memory Cache] Hit for: {query[:30]}...")
                return cached_data['results']
            else:
                # Remove expired entry
                del self.memory_cache[cache_key]
        
        self.memory_stats['cache_misses'] += 1
        return None

    def _cache_memory_results(self, query: str, results: List[str]):
        """Cache memory results with TTL"""
        cache_key = self._get_cache_key(query)
        
        # Simple LRU: remove oldest entries if cache is full
        if len(self.memory_cache) >= self.cache_max_size:
            # Remove the oldest entry
            oldest_key = min(self.memory_cache.keys(), 
                           key=lambda k: self.memory_cache[k]['timestamp'])
            del self.memory_cache[oldest_key]
        
        self.memory_cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
        logger.debug(f"[Memory Cache] Stored results for: {query[:30]}...")

    async def _parallel_memory_search(self, queries: List[str], max_facts_per_query: int = 2) -> List[str]:
        """Perform parallel memory searches with timeout using MCP or REST fallback"""
        if not queries:
            return []
        
        async def search_single_query(query: str):
            try:
                # Use timeout to prevent hanging
                result = await asyncio.wait_for(
                    self._search_memory_facts(query=query, max_facts=max_facts_per_query),
                    timeout=self.memory_search_timeout
                )
                return result or []
            except asyncio.TimeoutError:
                logger.debug(f"Memory search timed out for: {query}")
                return []
            except Exception as e:
                logger.debug(f"Memory search failed for '{query}': {e}")
                return []
        
        # Execute all searches in parallel
        try:
            tasks = [search_single_query(query) for query in queries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Flatten results and filter out exceptions
            all_facts = []
            for result in results:
                if isinstance(result, list):
                    all_facts.extend(result)
            
            return all_facts
        
        except Exception as e:
            logger.debug(f"Parallel search failed: {e}")
            return []

    async def _search_memory_facts(self, query: str, max_facts: int = 5) -> List[str]:
        """Simplified: disable REST memory search; rely on MCP tools or conversation context only."""
        return []

    def _search_local_memory(self, query: str, max_facts: int = 5) -> List[str]:
        """Simplified: no local memory search results."""
        return []



    async def on_enter(self):
        # Initialize without automatic greeting - user will initiate conversation
        # This prevents issues with TTS/LLM not being ready
        logger.info("🚀 on_enter() called - starting session initialization")
        self.conversation_start_time = datetime.utcnow()
        
        # Apply global system prompt
        try:
            from core.global_settings_manager import global_settings_manager
            logger.info("📝 Starting global prompt combination...")
            combined_prompt = await self._combine_prompts(self.preset.system_prompt)
            enhanced_prompt = self._enhance_prompt_with_memory(combined_prompt)
            
            # Store the enhanced prompt for use in conversation
            self._enhanced_instructions = enhanced_prompt
            
            # CRITICAL: Update the Agent's instructions using the proper method
            await self.update_instructions(enhanced_prompt)
            
            logger.info("✅ Global system prompt combined and stored successfully")
            logger.info(f"📊 Final prompt length: {len(enhanced_prompt)} characters")
        except Exception as e:
            logger.warning(f"⚠️  Failed to apply global system prompt: {e}")
            # Fallback to just the agent prompt with memory enhancement
            enhanced_prompt = self._enhance_prompt_with_memory(self.preset.system_prompt)
            self._enhanced_instructions = enhanced_prompt
            await self.update_instructions(enhanced_prompt)
        
        # Check MCP server availability (simplified: rely solely on MCP; internal memory disabled)
        try:
            if hasattr(self, 'session') and hasattr(self.session, 'mcp_servers') and self.session.mcp_servers:
                logger.info(f"✅ MCP connected: {len(self.session.mcp_servers)} server(s)")
                for i, server in enumerate(self.session.mcp_servers):
                    logger.info(f"  - MCP Server {i+1}: {type(server).__name__} ({getattr(server, 'url', 'N/A')})")
            else:
                logger.warning("❗ No MCP servers found in session; tools will be unavailable")
        except RuntimeError as e:
            logger.debug(f"Session not available yet: {e}")

    @function_tool
    async def get_current_time(self, location: str = "local", timezone_name: str = "") -> str:
        """Get the current time for a specific location or timezone. Defaults to London timezone if not specified."""
        import pytz
        from datetime import datetime
        
        logger.info(f"🕐 Getting current time for {location} (timezone: {timezone_name})")
        
        try:
            # Default to London timezone if no specific timezone is provided
            if not timezone_name and location.lower() not in ["local", "here"]:
                timezone_name = "Europe/London"
                logger.info(f"Defaulting to London timezone: {timezone_name}")
            
            # Handle local time requests
            if location.lower() in ["local", "here"] and not timezone_name:
                # Use system local time
                current_time = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
                return f"The current local time is {current_time}."
            
            # Handle timezone requests
            if timezone_name:
                try:
                    tz = pytz.timezone(timezone_name)
                    # Use timezone-aware datetime
                    current_time = datetime.now(tz).strftime("%I:%M %p on %A, %B %d, %Y %Z")
                    return f"The current time in {timezone_name} is {current_time}."
                except pytz.exceptions.UnknownTimeZoneError:
                    return f"I don't recognize the timezone '{timezone_name}'. Please try a timezone like 'America/New_York', 'Europe/London', or 'Asia/Tokyo'."
            
            # Handle common location names
            location_timezones = {
                "new york": "America/New_York",
                "london": "Europe/London", 
                "tokyo": "Asia/Tokyo",
                "paris": "Europe/Paris",
                "sydney": "Australia/Sydney",
                "los angeles": "America/Los_Angeles",
                "chicago": "America/Chicago",
                "denver": "America/Denver",
                "miami": "America/New_York",
                "berlin": "Europe/Berlin",
                "moscow": "Europe/Moscow",
                "mumbai": "Asia/Kolkata",
                "singapore": "Asia/Singapore",
                "hong kong": "Asia/Hong_Kong",
                "beijing": "Asia/Shanghai",
                "uk": "Europe/London",
                "united kingdom": "Europe/London",
                "britain": "Europe/London",
                "england": "Europe/London"
            }
            
            location_lower = location.lower()
            if location_lower in location_timezones:
                tz = pytz.timezone(location_timezones[location_lower])
                current_time = datetime.now(tz).strftime("%I:%M %p on %A, %B %d, %Y %Z")
                return f"The current time in {location} is {current_time}."
            
            # If location not found, return London time as default
            tz = pytz.timezone("Europe/London")
            current_time = datetime.now(tz).strftime("%I:%M %p on %A, %B %d, %Y %Z")
            return f"I couldn't find the timezone for '{location}'. The current time in London is {current_time}. Try specifying a timezone like 'America/New_York' for more accurate results."
            
        except Exception as e:
            logger.error(f"Error getting time: {e}")
            # Fallback to system time if there's an error
            try:
                current_time = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
                return f"I'm sorry, I had trouble with the timezone. The current local time is {current_time}."
            except:
                return "I'm sorry, I couldn't get the current time right now. Please try again."

    @function_tool
    async def get_current_date(self, format_type: str = "full") -> str:
        """Get the current date in various formats. Defaults to London timezone."""
        import pytz
        from datetime import datetime
        
        logger.info(f"📅 Getting current date (format: {format_type})")
        try:
            # Use London timezone by default for consistency
            tz = pytz.timezone("Europe/London")
            now = datetime.now(tz)
            
            if format_type.lower() == "short":
                date_str = now.strftime("%m/%d/%Y")
            elif format_type.lower() == "iso":
                date_str = now.strftime("%Y-%m-%d")
            elif format_type.lower() == "numeric":
                date_str = now.strftime("%Y%m%d")
            else:  # full format
                date_str = now.strftime("%A, %B %d, %Y")
            
            return f"Today is {date_str}."
        except Exception as e:
            logger.error(f"Error getting date: {e}")
            # Fallback to system time if there's an error
            try:
                now = datetime.now()
                if format_type.lower() == "short":
                    date_str = now.strftime("%m/%d/%Y")
                elif format_type.lower() == "iso":
                    date_str = now.strftime("%Y-%m-%d")
                elif format_type.lower() == "numeric":
                    date_str = now.strftime("%Y%m%d")
                else:  # full format
                    date_str = now.strftime("%A, %B %d, %Y")
                return f"Today is {date_str}."
            except:
                return "I'm sorry, I couldn't get the current date right now."

    @function_tool
    async def calculate_math(self, expression: str) -> str:
        """Perform basic mathematical calculations safely."""
        import re
        
        logger.info(f"🧮 Calculating: {expression}")
        try:
            # Simple safe evaluation for basic math
            # Only allow numbers, operators, and basic functions
            if re.match(r'^[0-9+\-*/().\s]+$', expression):
                result = eval(expression)
                return f"The result of {expression} is {result}."
            else:
                return f"I can only calculate basic mathematical expressions with numbers and operators (+, -, *, /, parentheses). Please provide a simpler expression."
        except Exception as e:
            logger.error(f"Error calculating: {e}")
            return "I'm sorry, I couldn't calculate that expression. Please check the format and try again."

    @function_tool
    async def get_day_of_week(self, date_str: str = "") -> str:
        """Get the day of the week for today or a specific date. Defaults to London timezone."""
        import pytz
        from datetime import datetime
        
        logger.info(f"📅 Getting day of week for: {date_str or 'today'}")
        try:
            if not date_str:
                # Use London timezone for consistency
                tz = pytz.timezone("Europe/London")
                now = datetime.now(tz)
                day = now.strftime("%A")
                date_str = now.strftime("%B %d, %Y")
                return f"Today ({date_str}) is {day}."
            
            # Try to parse the date string
            try:
                # Handle various date formats
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%d %B %Y"]:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        day = date_obj.strftime("%A")
                        formatted_date = date_obj.strftime("%B %d, %Y")
                        return f"{formatted_date} is a {day}."
                    except ValueError:
                        continue
                
                return f"I couldn't parse the date '{date_str}'. Please try formats like '2025-01-15', '01/15/2025', or 'January 15, 2025'."
                
            except Exception as e:
                return f"I had trouble parsing that date format. Please try a format like '2025-01-15' or 'January 15, 2025'."
                
        except Exception as e:
            logger.error(f"Error getting day of week: {e}")
            # Fallback to system time if there's an error
            try:
                if not date_str:
                    day = datetime.now().strftime("%A")
                    return f"Today is {day}."
                else:
                    return f"I'm sorry, I couldn't determine the day of the week for '{date_str}' right now."
            except:
                return "I'm sorry, I couldn't determine the day of the week right now."

    @function_tool
    async def get_current_year(self) -> str:
        """Get the current year. Defaults to London timezone."""
        import pytz
        from datetime import datetime
        
        logger.info("📅 Getting current year")
        try:
            # Use London timezone for consistency
            tz = pytz.timezone("Europe/London")
            now = datetime.now(tz)
            year = now.strftime("%Y")
            return f"The current year is {year}."
        except Exception as e:
            logger.error(f"Error getting year: {e}")
            # Fallback to system time if there's an error
            try:
                year = datetime.now().strftime("%Y")
                return f"The current year is {year}."
            except:
                return "I'm sorry, I couldn't get the current year right now."

    @function_tool
    async def get_timezone_info(self, timezone_name: str) -> str:
        """Get information about a specific timezone."""
        import pytz
        from datetime import datetime
        
        logger.info(f"🌍 Getting timezone info for: {timezone_name}")
        try:
            tz = pytz.timezone(timezone_name)
            now = datetime.now(tz)
            utc_offset = now.strftime("%z")
            
            # Format UTC offset nicely
            if len(utc_offset) >= 5:
                formatted_offset = f"UTC{utc_offset[:3]}:{utc_offset[3:5]}"
            else:
                formatted_offset = utc_offset
            
            current_time = now.strftime("%I:%M %p on %A, %B %d, %Y")
            
            return f"Timezone {timezone_name}: Current time is {current_time}, UTC offset is {formatted_offset}."
            
        except Exception as e:
            if "Unknown" in str(e):
                return f"I don't recognize the timezone '{timezone_name}'. Please try a timezone like 'America/New_York', 'Europe/London', or 'Asia/Tokyo'."
            logger.error(f"Error getting timezone info: {e}")
            return "I'm sorry, I couldn't get timezone information right now."

    @function_tool 
    async def help_with_tools(self) -> str:
        """Show available tools and capabilities."""
        logger.info("📋 Showing available tools")
        return f"""I'm {self.preset_name} and I have access to several tools:
        
Built-in tools:
• Current time and date (with timezone support - defaults to London)
• Current year
• Day of the week calculations  
• Timezone information and conversions
• Basic math calculations
• General conversation and assistance

External tools (when available):
• Memory and knowledge graph via Graphiti
• Other services as configured in this preset

My current configuration:
• Voice: {self.preset.voice_config.provider} - {self.preset.voice_config.voice}
• LLM: {self.preset.llm_config.provider} - {self.preset.llm_config.model}
• STT: {self.preset.stt_config.provider} - {self.preset.stt_config.model}

Just ask me naturally and I'll use the right tool to help you! For example:
- "What time is it in Tokyo?"
- "What year is it?"
- "What day of the week is Christmas?"
- "Calculate 25 * 4 + 8"
- "Remember that I prefer meetings in the morning"
"""

    @function_tool
    async def get_agent_info(self) -> str:
        """Get information about the current agent preset and capabilities"""
        return f"I am currently configured as '{self.preset_name}': {self.preset.description}. I have access to {len(self.preset.mcp_server_ids)} specialized tools and services."

    @function_tool
    async def check_memory_status(self) -> str:
        """Check the status of memory systems and tools available to the agent"""
        logger.info("🔍 Checking memory system status")
        
        status_parts = []
        
        # Check Graphiti REST API connectivity
        try:
            resp = requests.get(f"{self.GRAPHITI_API_URL}/healthcheck", timeout=3)
            if resp.ok:
                status_parts.append("✅ Graphiti REST API: Connected")
                self.memory_api_available = True
            else:
                status_parts.append(f"❌ Graphiti REST API: Error {resp.status_code}")
                self.memory_api_available = False
        except Exception as e:
            status_parts.append(f"❌ Graphiti REST API: Connection failed - {e}")
            self.memory_api_available = False
        
        # Check MCP tools available through session
        mcp_tools_count = 0
        if hasattr(self, 'session') and self.session and hasattr(self.session, 'mcp_servers'):
            mcp_servers = getattr(self.session, 'mcp_servers', [])
            if mcp_servers:
                status_parts.append(f"✅ MCP Servers: {len(mcp_servers)} connected")
                for i, server in enumerate(mcp_servers):
                    server_info = f"  - Server {i+1}: {type(server).__name__}"
                    if hasattr(server, 'url'):
                        server_info += f" ({server.url})"
                    status_parts.append(server_info)
                    
                    # Try to count tools
                    try:
                        if hasattr(server, 'list_tools'):
                            tools = await server.list_tools()
                            mcp_tools_count += len(tools) if tools else 0
                            status_parts.append(f"    Tools: {len(tools) if tools else 0}")
                    except Exception as e:
                        status_parts.append(f"    Tools: Error listing - {e}")
            else:
                status_parts.append("❌ MCP Servers: None connected")
        else:
            status_parts.append("❌ MCP Servers: Session not available")
        
        # Check memory statistics
        stats = self.get_memory_stats()
        status_parts.append(f"\n📊 Memory Statistics:")
        status_parts.append(f"  - Memories retrieved: {stats['memories_retrieved']}")
        status_parts.append(f"  - Memories stored: {stats['memories_stored']}")
        status_parts.append(f"  - Local session memories: {len(self.local_memory)}")
        status_parts.append(f"  - Conversation turns: {self.conversation_turns}")
        
        # Configuration info
        status_parts.append(f"\n🔧 Configuration:")
        status_parts.append(f"  - Graphiti MCP URL: {self.GRAPHITI_MCP_URL}")
        status_parts.append(f"  - Graphiti API URL: {self.GRAPHITI_API_URL}")
        status_parts.append(f"  - Preset MCP servers: {self.preset.mcp_server_ids}")
        status_parts.append(f"  - Total MCP tools detected: {mcp_tools_count}")
        
        result = "\n".join(status_parts)
        logger.info(f"Memory status check result:\n{result}")
        return result

    # =============================================================================
    # MEMORY SYSTEM METHODS (Enhanced from GraphitiAgent)
    # =============================================================================

    def extract_search_keywords(self, user_input: str) -> List[str]:
        """Extract relevant keywords and concepts for memory search"""
        # Common words to filter out
        stop_words = {'i', 'me', 'my', 'you', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'can', 'may', 'might', 'what', 'when', 'where', 'why', 'how', 'who', 'which', 'that', 'this', 'these', 'those'}
        
        # Extract words and filter out stop words
        words = re.findall(r'\b\w+\b', user_input.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Also generate concept-based searches
        concepts = []
        
        # Detect question types and add relevant concepts
        if any(word in user_input.lower() for word in ['food', 'eat', 'meal', 'diet', 'nutrition']):
            concepts.extend(['pet', 'dog', 'cat', 'animal', 'dietary', 'preferences'])
        
        if any(word in user_input.lower() for word in ['recommend', 'suggest', 'advice', 'should', 'best']):
            concepts.extend(['preferences', 'likes', 'dislikes', 'interests'])
            
        if any(word in user_input.lower() for word in ['travel', 'trip', 'vacation', 'visit']):
            concepts.extend(['location', 'places', 'destinations'])
            
        if any(word in user_input.lower() for word in ['work', 'job', 'career', 'project']):
            concepts.extend(['work', 'profession', 'company', 'project'])
        
        # Combine keywords and concepts, return unique items
        all_terms = list(set(keywords + concepts))
        return all_terms[:10]  # Limit to avoid too many searches

    def is_explicit_memory_trigger(self, user_input: str) -> bool:
        """Check for explicit memory-related queries"""
        triggers = [
            r"remember", r"what do you know about", r"do you remember", r"tell me about my", 
            r"recall", r"past conversation", r"previous", r"before", r"earlier"
        ]
        return any(re.search(trigger, user_input, re.IGNORECASE) for trigger in triggers)

    def is_memory_worthy(self, user_input: str) -> bool:
        """Determine if user input contains information worth storing"""
        # Patterns that indicate personal information sharing
        personal_patterns = [
            r"i am", r"i work", r"i like", r"i love", r"i hate", r"i prefer", r"i have", r"i own",
            r"my name", r"my project", r"my company", r"my dog", r"my cat", r"my pet", r"my family",
            r"i live", r"i study", r"i enjoy", r"i dislike", r"i need", r"i want"
        ]
        
        # Information that suggests facts about the user
        return any(re.search(pattern, user_input, re.IGNORECASE) for pattern in personal_patterns)

    async def retrieve_contextual_memory(self, user_input: str) -> List[str]:
        """Optimized memory retrieval with caching, parallel searches, and smart filtering"""
        start_time = time.time()
        
        # Early exit for queries that don't need memory
        if self._should_skip_memory_search(user_input):
            logger.debug(f"[Memory] Skipped search for: '{user_input[:30]}...' (filtered)")
            return []
        
        self.memory_stats['searches_performed'] += 1
        
        # Check cache first
        cached_results = self._get_cached_memory(user_input)
        if cached_results is not None:
            search_time = time.time() - start_time
            self.memory_stats['search_times'].append(search_time)
            self.memory_stats['memories_retrieved'] += len(cached_results)
            logger.debug(f"[Memory] Cache hit in {search_time:.3f}s: {len(cached_results)} memories")
            return cached_results
        
        # Prepare search queries for parallel execution
        search_queries = [user_input]  # Always include direct query
        
        # Add strategic keyword searches only for relevant queries
        if not self.is_explicit_memory_trigger(user_input):
            keywords = self.extract_search_keywords(user_input)
            # Be more selective - only add top 2 keywords to reduce latency
            search_queries.extend(keywords[:2])
        else:
            # For explicit memory triggers, add a broad search
            search_queries.append("user personal information")
        
        try:
            # Execute all searches in parallel with timeout
            all_facts = await self._parallel_memory_search(search_queries, max_facts_per_query=2)
            
            # Fast deduplication using set
            unique_facts = []
            seen = set()
            for fact in all_facts:
                if fact and fact.strip():
                    fact_clean = fact.strip()
                    if fact_clean not in seen:
                        unique_facts.append(fact_clean)
                        seen.add(fact_clean)
                        if len(unique_facts) >= 5:  # Early termination
                            break
            
            # Cache the results for future use
            self._cache_memory_results(user_input, unique_facts)
            
        except Exception as e:
            logger.warning(f"Memory retrieval error: {e}")
            unique_facts = []
        
        # Update performance statistics
        search_time = time.time() - start_time
        self.memory_stats['search_times'].append(search_time)
        self.memory_stats['last_search_time'] = search_time
        
        if unique_facts:
            self.memory_stats['memories_retrieved'] += len(unique_facts)
            logger.debug(f"[Memory] Retrieved {len(unique_facts)} memories in {search_time:.3f}s")
        else:
            logger.debug(f"[Memory] No memories found in {search_time:.3f}s")
        
        # Update success rate (under 1.5s is considered fast)
        total_searches = self.memory_stats['searches_performed']
        successful_searches = sum(1 for t in self.memory_stats['search_times'] if t < 1.5)
        self.memory_stats['retrieval_success_rate'] = successful_searches / total_searches if total_searches > 0 else 0.0
        
        return unique_facts

    async def store_memory(self, episode_body: str, name: str = None):
        """Store information to memory using Graphiti REST API (/messages) with local fallback"""
        try:
            episode_name = name or f"Voice Memory {datetime.utcnow().isoformat()}"
            
            payload = {
                "group_id": "global",
                "messages": [
                    {
                        "content": episode_body,
                        "role_type": "assistant",
                        "role": "assistant",
                        "name": episode_name,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                ]
            }
            if not self.memory_api_available or self._is_placeholder_graphiti_url(self.GRAPHITI_API_URL):
                # Local-only mode
                self.local_memory.append(payload)
                self.memory_stats['memories_stored'] += 1
                self._emit_memory_event('memory-fallback', "Saved to local session memory (offline)")
                return

            base = self.GRAPHITI_API_URL.rstrip('/')
            # Graphiti messages ingestion endpoint
            endpoints = [f"{base}/messages", f"{base}/api/messages"]
            resp = None
            for url in endpoints:
                try:
                    r = requests.post(url, json=payload, timeout=5)
                except Exception:
                    continue
                # Accept 200/201/202 as success
                if r.status_code in (200, 201, 202):
                    resp = r
                    break
            if resp is None:
                raise RuntimeError("All message ingestion endpoints failed")
            if resp.status_code in (200, 201, 202):
                logger.info(f"[Graphiti] Stored memory via REST: {episode_name}")
                self.memory_stats['memories_stored'] += 1
                self._emit_memory_event('memory-created', "New memory saved")
            else:
                logger.warning(f"[Graphiti] Memory storage failed: {resp.status_code}: {resp.text}")
                self.local_memory.append(payload)
                self._emit_memory_event('memory-fallback', "Saved to local session memory")
                    
        except Exception as e:
            logger.warning(f"[Graphiti] Memory storage error: {e}")
            self.local_memory.append({"name": "Local Session", "episode_body": episode_body})
            self._emit_memory_event('memory-fallback', "Saved to local session memory only")

    def get_memory_stats(self) -> dict:
        """Get current memory performance statistics"""
        stats = self.memory_stats.copy()
        
        # Calculate average search time
        if stats['search_times']:
            stats['average_search_time'] = sum(stats['search_times']) / len(stats['search_times'])
            stats['max_search_time'] = max(stats['search_times'])
            stats['min_search_time'] = min(stats['search_times'])
        else:
            stats['average_search_time'] = 0.0
            stats['max_search_time'] = 0.0
            stats['min_search_time'] = 0.0
        
        # Calculate memory efficiency
        if stats['searches_performed'] > 0:
            stats['memories_per_search'] = stats['memories_retrieved'] / stats['searches_performed']
        else:
            stats['memories_per_search'] = 0.0
        
        return stats

    # -----------------------------------------------------------------
    # Front-end Event Helpers
    # -----------------------------------------------------------------

    def _emit_memory_event(self, event_type: str, message: str = "") -> None:  # noqa: D401
        """Emit a memory-related event to the client via LiveKit data channel.

        This helper marshals the *event_type* and *message* into a JSON
        payload and publishes it over the **reliable** data channel so the
        React UI can pick it up and trigger animations.  The call is non-
        blocking – we schedule the coroutine with *asyncio.create_task* so
        we don't slow down the agent's critical path.
        """

        try:
            # Debug: Check if session is available
            logger.info(f"🔍 _emit_memory_event called with type: {event_type}, message: {message}")
            
            try:
                session = self.session
                logger.info(f"✅ Session available: {session is not None}")
            except RuntimeError as e:
                logger.info(f"❌ Session not available: {e}")
                return
                
            room = getattr(self.session, "room", None)  # populated after session.start()
            logger.info(f"🏠 Room available: {room is not None}, connected: {room.isconnected() if room else False}")
            
            if room and room.isconnected():
                import json, asyncio
                payload = json.dumps({"type": event_type, "message": message}).encode()
                logger.info(f"📤 Publishing memory event: {payload}")

                async def _publish() -> None:
                    try:
                        from livekit import rtc  # type: ignore

                        await room.local_participant.publish_data(
                            payload,
                            reliable=True,
                        )
                        logger.info(f"✅ Memory event published successfully")
                    except Exception as e:  # pragma: no cover
                        logger.warning(f"❌ Failed to publish memory event: {e}")

                asyncio.create_task(_publish())
            else:
                logger.info(f"❌ Cannot publish memory event - room not available or not connected")
                # Wait for room connection with timeout
                async def _wait_and_publish():
                    import asyncio
                    max_wait = 5.0  # Wait up to 5 seconds
                    wait_interval = 0.5
                    waited = 0.0
                    
                    while waited < max_wait:
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval
                        
                        if room and room.isconnected():
                            try:
                                payload = json.dumps({"type": event_type, "message": message}).encode()
                                await room.local_participant.publish_data(
                                    payload,
                                    reliable=True,
                                )
                                logger.info(f"✅ Memory event published successfully after waiting {waited:.1f}s")
                                return
                            except Exception as e:
                                logger.warning(f"❌ Failed to publish memory event after waiting: {e}")
                                return
                    
                    logger.warning(f"❌ Timeout waiting for room connection after {max_wait}s")
                
                asyncio.create_task(_wait_and_publish())
        except Exception as e:
            logger.warning(f"❌ Error emitting memory event: {e}")

    def _emit_tool_event(self, tool_name: str) -> None:  # noqa: D401
        """Emit a *tool-called* event so the UI can display a particle burst."""

        try:
            # Debug: Check if session is available
            logger.info(f"🔍 _emit_tool_event called with tool: {tool_name}")
            
            try:
                session = self.session
                logger.info(f"✅ Session available: {session is not None}")
            except RuntimeError as e:
                logger.info(f"❌ Session not available: {e}")
                return
                
            room = getattr(self.session, "room", None)
            logger.info(f"🏠 Room available: {room is not None}, connected: {room.isconnected() if room else False}")
            
            if room and room.isconnected():
                import json, asyncio

                payload = json.dumps({"type": "tool-called", "tool": tool_name}).encode()
                logger.info(f"📤 Publishing tool event: {payload}")

                async def _publish() -> None:
                    try:
                        from livekit import rtc  # type: ignore

                        await room.local_participant.publish_data(
                            payload,
                            reliable=True,
                        )
                        logger.info(f"✅ Tool event published successfully")
                    except Exception as e:
                        logger.warning(f"❌ Failed to publish tool event: {e}")

                asyncio.create_task(_publish())
            else:
                logger.info(f"❌ Cannot publish tool event - room not available or not connected")
                # Wait for room connection with timeout
                async def _wait_and_publish():
                    import asyncio
                    max_wait = 5.0  # Wait up to 5 seconds
                    wait_interval = 0.5
                    waited = 0.0
                    
                    while waited < max_wait:
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval
                        
                        if room and room.isconnected():
                            try:
                                payload = json.dumps({"type": "tool-called", "tool": tool_name}).encode()
                                await room.local_participant.publish_data(
                                    payload,
                                    reliable=True,
                                )
                                logger.info(f"✅ Tool event published successfully after waiting {waited:.1f}s")
                                return
                            except Exception as e:
                                logger.warning(f"❌ Failed to publish tool event after waiting: {e}")
                                return
                    
                    logger.warning(f"❌ Timeout waiting for room connection after {max_wait}s")
                
                asyncio.create_task(_wait_and_publish())
        except Exception as e:  # pragma: no cover
            logger.warning(f"❌ Error emitting tool event: {e}")

    # =============================================================================
    # Audio Processing Optimization Methods
    # =============================================================================
    
    async def tts_node(self, text: AsyncIterable[str], model_settings: ModelSettings):
        """Enhanced TTS node with optional audio speedup processing"""
        if self.enable_audio_speedup:
            return self._process_audio_stream(Agent.default.tts_node(self, text, model_settings))
        return Agent.default.tts_node(self, text, model_settings)
    
    async def realtime_audio_output_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> AsyncIterable[rtc.AudioFrame]:
        """Enhanced realtime audio output with optional speedup processing"""
        if self.enable_audio_speedup:
            return self._process_audio_stream(
                Agent.default.realtime_audio_output_node(self, audio, model_settings)
            )
        return Agent.default.realtime_audio_output_node(self, audio, model_settings)
    
    async def _process_audio_stream(
        self, audio: AsyncIterable[rtc.AudioFrame]
    ) -> AsyncIterable[rtc.AudioFrame]:
        """Process audio stream with speed optimization"""
        if not LIBROSA_AVAILABLE:
            # Fallback to original stream if librosa is not available
            async for frame in audio:
                yield frame
            return
            
        stream: utils.audio.AudioByteStream | None = None
        async for frame in audio:
            if stream is None:
                stream = utils.audio.AudioByteStream(
                    sample_rate=frame.sample_rate,
                    num_channels=frame.num_channels,
                    samples_per_channel=frame.sample_rate // 10,  # 100ms buffer
                )
            
            # Process audio in chunks for streaming
            for f in stream.push(frame.data):
                yield self._process_audio_frame(f)
        
        # Process remaining audio in buffer
        if stream:
            for f in stream.flush():
                yield self._process_audio_frame(f)
    
    def _process_audio_frame(self, frame: rtc.AudioFrame) -> rtc.AudioFrame:
        """Process individual audio frame with time-stretch optimization"""
        try:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(frame.data, dtype=np.int16)
            
            # Time-stretch without pitch change using librosa
            stretched = librosa.effects.time_stretch(
                audio_data.astype(np.float32) / np.iinfo(np.int16).max,
                rate=self.audio_speed_factor,
            )
            
            # Convert back to int16
            stretched = (stretched * np.iinfo(np.int16).max).astype(np.int16)
            
            return rtc.AudioFrame(
                data=stretched.tobytes(),
                sample_rate=frame.sample_rate,
                num_channels=frame.num_channels,
                samples_per_channel=stretched.shape[-1],
            )
        except Exception as e:
            logger.warning(f"Audio processing failed, using original frame: {e}")
            return frame

    # =============================================================================
    # Fast Pre-Response System
    # =============================================================================
    
    def _setup_fast_preresponse(self):
        """Initialize fast pre-response system with lightweight LLM"""
        try:
            # Use a fast, lightweight model for immediate responses
            from livekit.plugins import groq
            self._fast_llm = groq.LLM(model="llama-3.1-8b-instant")
            from livekit.agents.llm import ChatMessage as LLMChatMessage
            self._fast_llm_prompt = LLMChatMessage(
                role="system",
                content=[
                    "Generate a brief acknowledgment response (5-10 words) to show you're processing the user's input.",
                    "Examples: 'Let me think about that...', 'That's interesting...', 'Good question...'"
                ]
            )
            logger.info("🚀 Fast pre-response system enabled with Groq LLM")
        except ImportError:
            # Fallback to OpenAI if Groq is not available
            try:
                self._fast_llm = openai.LLM(model="gpt-4o-mini")
                from livekit.agents.llm import ChatMessage as LLMChatMessage
                self._fast_llm_prompt = LLMChatMessage(
                    role="system",
                    content=[
                        "Generate a brief acknowledgment response (5-10 words) to show you're processing the user's input.",
                        "Examples: 'Let me think about that...', 'That's interesting...', 'Good question...'"
                    ]
                )
                logger.info("🚀 Fast pre-response system enabled with OpenAI LLM")
            except Exception as e:
                logger.warning(f"Failed to setup fast pre-response system: {e}")
                self.enable_fast_preresponse = False

    async def on_user_turn_started(self, turn_ctx: ChatContext):
        """Pre-computation before the user speaks, used for warming up models"""
        if self.enable_fast_preresponse and self._fast_llm:
            asyncio.create_task(self._fast_llm.chat("NoOp", history=[]))  # Prewarm fast LLM
    
    async def on_user_turn_completed(self, turn_ctx: ChatContext, new_message: ChatMessage):
        """Enhanced user turn completion with fast pre-response and memory integration"""
        self.conversation_turns += 1
        user_input = new_message.text_content or ""
        self.conversation_history.append({'role': 'user', 'content': user_input, 'timestamp': datetime.utcnow().isoformat()})

        if self.enable_fast_preresponse and self._fast_llm:
            fast_llm_fut = asyncio.Future[str]()

            async def _fast_llm_reply() -> AsyncIterable[str]:
                # Use a separate context to avoid polluting the main LLM's turn
                fast_ctx = turn_ctx.copy(exclude_instructions=True, exclude_function_call=True).truncate(max_items=3)
                if self._fast_llm_prompt:
                    fast_ctx.items.insert(0, self._fast_llm_prompt)
                fast_ctx.items.append(new_message)

                filler_response = ""
                try:
                    async for chunk in self._fast_llm.chat(chat_ctx=fast_ctx).to_str_iterable():
                        filler_response += chunk
                        yield chunk
                    fast_llm_fut.set_result(filler_response)
                except Exception as e:
                    logger.error(f"Fast LLM generation failed: {e}")
                    if not fast_llm_fut.done():
                        fast_llm_fut.set_exception(e)

            # Say the fast response without adding it to history yet
            self.session.say(_fast_llm_reply(), add_to_chat_ctx=False)

            try:
                # Wait for the fast response to be fully generated
                filler_response = await asyncio.wait_for(fast_llm_fut, timeout=5.0)
                logger.info(f"Fast response: {filler_response}")
                # Now add it to the turn context so the main LLM is aware
                turn_ctx.add_message(role="assistant", content=filler_response, interrupted=False)
            except asyncio.TimeoutError:
                logger.warning("Fast response generation timed out.")
            except Exception as e:
                logger.error(f"Error processing fast response: {e}")

        # Always attempt to retrieve relevant memories for context
        logger.info(f"🧠 About to retrieve memories for: '{user_input[:50]}...'")
        relevant_memories = await self.retrieve_contextual_memory(user_input)
        logger.info(f"🧠 Retrieved {len(relevant_memories)} memories: {relevant_memories[:2] if relevant_memories else 'None'}")
        
        # Build enhanced system prompt with memory context
        # Use enhanced instructions if available, otherwise fall back to original
        base_prompt = getattr(self, '_enhanced_instructions', self.instructions)
        system_prompt = base_prompt
        
        # Debug logging to verify enhanced instructions are being used
        if hasattr(self, '_enhanced_instructions'):
            logger.info(f"🎯 Using enhanced instructions with global prompt (length: {len(base_prompt)})")
        else:
            logger.info(f"⚠️  Using original instructions (no global prompt applied)")
        if relevant_memories:
            memory_context = "\n".join(f"- {fact}" for fact in relevant_memories)
            system_prompt += f"\n\nRelevant information from your memory:\n{memory_context}"
            self.memory_context = memory_context
            logger.debug(f"[Graphiti] Injected {len(relevant_memories)} memories into context")
        else:
            self.memory_context = ""
        
        # Set the enhanced system prompt (if session has LLM access)
        if hasattr(self, 'session') and hasattr(self.session, 'llm') and self.session.llm:
            self.session.llm.system_prompt = system_prompt
        
        # Store memory if the input contains meaningful personal information
        if self.is_memory_worthy(user_input):
            await self.store_memory(user_input, f"User Info - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
        
        # Call parent implementation if it exists
        if hasattr(super(), 'on_user_turn_completed'):
            await super().on_user_turn_completed(turn_ctx, new_message)

    async def on_agent_speech_committed(self, message: ChatMessage):
        """Store agent responses for conversation history"""
        if message.text_content:
            self.conversation_history.append({'role': 'assistant', 'content': message.text_content, 'timestamp': datetime.utcnow().isoformat()})
        
        # Call parent implementation if it exists
        if hasattr(super(), 'on_agent_speech_committed'):
            await super().on_agent_speech_committed(message)

    async def on_disconnect(self):
        """Enhanced disconnect with memory performance logging and conversation storage"""
        # Log memory performance statistics
        if self.conversation_turns > 0:
            self.log_memory_performance()
        
        # Store conversation transcript if it meets threshold
        if self.conversation_turns >= self.memory_threshold and len(self.conversation_history) > 0:
            conversation_summary = {
                'session_start': self.conversation_start_time.isoformat() if self.conversation_start_time else None,
                'session_end': datetime.utcnow().isoformat(),
                'total_turns': self.conversation_turns,
                'conversation_history': self.conversation_history
            }
            await self.store_session_transcript(conversation_summary)
        
        # Call parent implementation if it exists
        if hasattr(super(), 'on_disconnect'):
            await super().on_disconnect()

    async def store_session_transcript(self, conversation_data: dict):
        """Store the full conversation transcript to memory"""
        try:
            transcript = "\n".join([
                f"{turn['role']}: {turn['content']}" 
                for turn in conversation_data.get('conversation_history', [])
            ])
            
            session_name = f"Conversation Session - {conversation_data.get('session_start', 'Unknown')[:16]}"
            await self.store_memory(transcript, session_name)
            logger.info("✅ Stored conversation transcript to memory")
            
        except Exception as e:
            logger.error(f"Error storing conversation transcript: {e}")

    # Initialize memory system when entering conversation
    # Note: on_enter method is defined earlier in the class with global prompt logic

    def configure_memory_performance(self, profile: str = "balanced"):
        """Configure memory system for different performance profiles
        
        Profiles:
        - 'fast': Minimal latency, basic memory functionality
        - 'balanced': Good balance of features and performance (default)
        - 'comprehensive': Full memory capabilities, higher latency acceptable
        """
        if profile == "fast":
            self.memory_search_timeout = 0.8
            self.min_query_length = 5
            self.cache_ttl = 600  # 10 minutes
            self.cache_max_size = 50
            # More aggressive skip patterns
            self.skip_patterns.extend([
                r'^(what|how|when|where|why)\s+\w+\?*$',  # Simple questions
                r'^(can|could|would|will)\s+you\s+\w+',   # Basic requests
            ])
            logger.info("🚀 Memory configured for FAST performance")
            
        elif profile == "comprehensive":
            self.memory_search_timeout = 3.0
            self.min_query_length = 2
            self.cache_ttl = 180  # 3 minutes (fresher results)
            self.cache_max_size = 200
            # Fewer skip patterns for comprehensive search
            self.skip_patterns = [
                r'^(hi|hello|hey|ok|okay|yes|no)$',
            ]
            logger.info("🔍 Memory configured for COMPREHENSIVE search")
            
        else:  # balanced (default)
            self.memory_search_timeout = 1.5
            self.min_query_length = 3
            self.cache_ttl = 300  # 5 minutes
            self.cache_max_size = 100
            logger.info("⚖️ Memory configured for BALANCED performance")

    def clear_memory_cache(self):
        """Clear the memory cache (useful for testing or manual refresh)"""
        cache_size = len(self.memory_cache)
        self.memory_cache.clear()
        logger.info(f"🧹 Cleared memory cache ({cache_size} entries)")
        
    def get_memory_cache_stats(self) -> dict:
        """Get detailed cache statistics"""
        return {
            'cache_size': len(self.memory_cache),
            'cache_max_size': self.cache_max_size,
            'cache_hits': self.memory_stats['cache_hits'],
            'cache_misses': self.memory_stats['cache_misses'],
            'hit_rate': self.memory_stats['cache_hits'] / (self.memory_stats['cache_hits'] + self.memory_stats['cache_misses']) if (self.memory_stats['cache_hits'] + self.memory_stats['cache_misses']) > 0 else 0.0,
            'oldest_entry_age': min((time.time() - entry['timestamp'] for entry in self.memory_cache.values()), default=0),
            'cache_ttl': self.cache_ttl
        }


async def create_tts_from_config(voice_config: VoiceConfig):
    """Create TTS instance with robust error handling and fallback"""
    try:
        return await _try_create_tts_with_fallback(voice_config)
    except Exception as e:
        logger.error(f"Failed to create TTS from config: {e}")
        return _create_fallback_openai_tts()


async def _try_create_tts_with_fallback(voice_config: VoiceConfig):
    """Try to create TTS with the requested provider, fallback to OpenAI if it fails"""
    
    # Get API key for the provider
    api_key = await api_key_manager.get_api_key(voice_config.provider)
    
    if voice_config.provider == "openai":
        return await _create_openai_tts(voice_config, api_key)
        
    elif voice_config.provider == "elevenlabs":
        return await _create_elevenlabs_tts_with_fallback(voice_config, api_key)
        
    elif voice_config.provider == "cartesia":
        return await _create_cartesia_tts_with_fallback(voice_config, api_key)
        
    elif voice_config.provider == "deepgram":
        return await _create_deepgram_tts_with_fallback(voice_config, api_key)
        
    else:
        logger.warning(f"Unknown TTS provider: {voice_config.provider}, using OpenAI fallback")
        return _create_fallback_openai_tts()


async def _create_openai_tts(voice_config: VoiceConfig, api_key: str):
    """Create OpenAI TTS with validation"""
    # Valid OpenAI voices
    valid_voices = {"alloy", "ash", "ballad", "coral", "sage", "verse"}
    voice = voice_config.voice if voice_config.voice in valid_voices else "ash"
    
    kwargs = {'voice': voice, 'speed': voice_config.speed}
    if api_key:
        kwargs['api_key'] = api_key
    
    logger.info(f"Creating OpenAI TTS with voice: {voice}")
    return openai.TTS(**kwargs)


async def _create_elevenlabs_tts_with_fallback(voice_config: VoiceConfig, api_key: str):
    """Create ElevenLabs TTS with fallback to OpenAI if it fails"""
    if not api_key:
        logger.warning("No ElevenLabs API key found, falling back to OpenAI")
        return _create_fallback_openai_tts()
    
    try:
        from livekit.plugins import elevenlabs
        
        # Use a known working voice ID if the specified one seems invalid
        voice_id = voice_config.voice
        if not voice_id or len(voice_id) < 10:  # ElevenLabs IDs are typically longer
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - reliable fallback
            logger.info(f"Using fallback ElevenLabs voice: Rachel")
        
        tts_kwargs = {
            'voice_id': voice_id,
            'api_key': api_key,
            'voice_settings': elevenlabs.VoiceSettings(
                speed=voice_config.speed,
                stability=voice_config.stability or 0.5,
                similarity_boost=voice_config.similarity_boost or 0.75
            )
        }
        
        # Add model support if specified
        if voice_config.model:
            tts_kwargs['model'] = voice_config.model
            logger.info(f"Creating ElevenLabs TTS with voice: {voice_id}, model: {voice_config.model}")
        else:
            logger.info(f"Creating ElevenLabs TTS with voice: {voice_id}, default model")
        
        return elevenlabs.TTS(**tts_kwargs)
        
    except Exception as e:
        logger.warning(f"ElevenLabs TTS creation failed: {e}, falling back to OpenAI")
        return _create_fallback_openai_tts()


async def _create_cartesia_tts_with_fallback(voice_config: VoiceConfig, api_key: str):
    """Create Cartesia TTS with fallback to OpenAI if it fails"""
    if not api_key:
        logger.warning("No Cartesia API key found, falling back to OpenAI")
        return _create_fallback_openai_tts()
    
    try:
        tts_kwargs = {
            'voice': voice_config.voice,
            'speed': 'fast' if voice_config.speed > 1.1 else 'slow' if voice_config.speed < 0.9 else 'normal',
            'api_key': api_key
        }
        
        # Add model support if specified, otherwise use default
        if voice_config.model:
            tts_kwargs['model'] = voice_config.model
            logger.info(f"Creating Cartesia TTS with voice: {voice_config.voice}, model: {voice_config.model}")
        else:
            # Use sonic-2 as default - it's the most stable
            tts_kwargs['model'] = 'sonic-2'
            logger.info(f"Creating Cartesia TTS with voice: {voice_config.voice}, default model: sonic-2")
        
        return cartesia.TTS(**tts_kwargs)
        
    except Exception as e:
        logger.warning(f"Cartesia TTS creation failed: {e}, falling back to OpenAI")
        return _create_fallback_openai_tts()


async def _create_deepgram_tts_with_fallback(voice_config: VoiceConfig, api_key: str):
    """Create Deepgram TTS with fallback to OpenAI if it fails"""
    if not api_key:
        logger.warning("No Deepgram API key found, falling back to OpenAI")
        return _create_fallback_openai_tts()
    
    try:
        kwargs = {
            'voice': voice_config.voice,
            'speed': voice_config.speed,
            'api_key': api_key
        }
        
        logger.info(f"Creating Deepgram TTS with voice: {voice_config.voice}")
        return deepgram.TTS(**kwargs)
        
    except Exception as e:
        logger.warning(f"Deepgram TTS creation failed: {e}, falling back to OpenAI")
        return _create_fallback_openai_tts()


def _create_fallback_openai_tts():
    """Create a reliable OpenAI TTS fallback"""
    logger.info("Using OpenAI TTS fallback with voice: ash")
    return openai.TTS(voice="ash")


async def create_llm_from_config(llm_config: LLMConfig):
    """Create LLM instance based on configuration with API key management and tool compatibility"""
    try:
        # Check tool compatibility and adjust settings automatically
        from utils.model_compatibility import get_tool_support_recommendation
        try:
            tool_info = await get_tool_support_recommendation(llm_config.model, llm_config.provider)
            
            # Log compatibility information
            if not tool_info["supports_tools"]:
                logger.warning(f"⚠️ Model {llm_config.model} doesn't support function calls - tools will be disabled")
            elif not tool_info["supports_parallel_tools"] and llm_config.parallel_tool_calls:
                logger.info(f"ℹ️ Model {llm_config.model} doesn't support parallel tools - using basic tool calls")
                
        except Exception as e:
            logger.warning(f"Could not check tool compatibility for {llm_config.model}: {e}")
            tool_info = {"supports_tools": True, "supports_parallel_tools": True}  # Default assumption
        
        # Get API key for the provider
        api_key = await api_key_manager.get_api_key(llm_config.provider)
        
        if llm_config.provider == "openai":
            llm_kwargs = {
                'model': llm_config.model,
                'temperature': llm_config.temperature,
                'parallel_tool_calls': llm_config.parallel_tool_calls and tool_info.get("supports_parallel_tools", True)
            }
            if llm_config.max_tokens:
                llm_kwargs['max_tokens'] = llm_config.max_tokens
            if api_key:
                llm_kwargs['api_key'] = api_key
            return openai.LLM(**llm_kwargs)
            
        elif llm_config.provider == "groq":
            from livekit.plugins import groq
            kwargs = {
                'model': llm_config.model,
                'temperature': llm_config.temperature
            }
            if api_key:
                kwargs['api_key'] = api_key
            return groq.LLM(**kwargs)
            
        elif llm_config.provider == "anthropic":
            from livekit.plugins import anthropic
            kwargs = {
                'model': llm_config.model,
                'temperature': llm_config.temperature
            }
            if api_key:
                kwargs['api_key'] = api_key
            return anthropic.LLM(**kwargs)
            
        elif llm_config.provider == "google":
            from livekit.plugins import google
            kwargs = {
                'model': llm_config.model,
                'temperature': llm_config.temperature
            }
            if api_key:
                kwargs['api_key'] = api_key
            return google.LLM(**kwargs)
        elif llm_config.provider == "openrouter":
            # OpenRouter provides an OpenAI-compatible endpoint aggregating many models.
            base_url = "https://openrouter.ai/api/v1"  # Recommended base URL for OpenRouter
            or_kwargs = {
                'model': llm_config.model,
                'temperature': llm_config.temperature,
                'parallel_tool_calls': llm_config.parallel_tool_calls,
                'base_url': base_url,
            }
            if api_key:
                or_kwargs['api_key'] = api_key
            return openai.LLM(**or_kwargs)
        else:
            logger.warning(f"Unknown LLM provider: {llm_config.provider}, falling back to OpenAI")
            return openai.LLM(model="gpt-4o-mini")
    except Exception as e:
        logger.error(f"Error creating LLM for {llm_config.provider}: {e}")
        return openai.LLM(model="gpt-4o-mini")  # Fallback


def create_stt_from_config(stt_config: STTConfig):
    """Create STT instance based on configuration"""
    try:
        if stt_config.provider == "deepgram":
            return deepgram.STT(
                model=stt_config.model,
                language=stt_config.language
            )
        elif stt_config.provider == "openai":
            return openai.STT(
                language=stt_config.language if stt_config.language != "multi" else None
            )
        elif stt_config.provider == "groq":
            from livekit.plugins import groq
            return groq.STT()
        else:
            logger.warning(f"Unknown STT provider: {stt_config.provider}, falling back to Deepgram")
            return deepgram.STT(model="nova-3", language="multi")
    except Exception as e:
        logger.error(f"Error creating STT for {stt_config.provider}: {e}")
        return deepgram.STT(model="nova-3", language="multi")  # Fallback


async def load_vad_model(ctx: JobContext):
    """Load VAD model asynchronously with caching"""
    try:
        # Check if VAD is already cached in process userdata
        if "vad" in ctx.proc.userdata and ctx.proc.userdata["vad"]:
            logger.debug("Using cached VAD model")
            return ctx.proc.userdata["vad"]
        
        # Load VAD model (this can be slow)
        logger.debug("Loading VAD model...")
        vad = silero.VAD.load()
        
        # Cache it for future use
        ctx.proc.userdata["vad"] = vad
        logger.debug("VAD model loaded and cached")
        return vad
        
    except Exception as e:
        logger.warning(f"Failed to load VAD model: {e}")
        # Return a fallback or None
        return None

async def load_mcp_servers_for_preset(mcp_server_ids: List[str]) -> List[mcp.MCPServer]:
    """Load MCP servers specified in the preset plus default Graphiti server"""
    mcp_servers = []
    
    # Always add Graphiti MCP server for memory functionality
    # Resolve GRAPHITI_MCP_URL with derivation from GRAPHITI_API_URL when needed
    graphiti_mcp_url = os.getenv("GRAPHITI_MCP_URL", "").strip()
    if (not graphiti_mcp_url) or ("your-graphiti-instance.com" in graphiti_mcp_url):
        graphiti_api_url = os.getenv("GRAPHITI_API_URL", "").strip()
        if graphiti_api_url and "your-graphiti-instance.com" not in graphiti_api_url:
            graphiti_mcp_url = graphiti_api_url.rstrip("/") + "/sse"
    try:
        if (not graphiti_mcp_url) or ("your-graphiti-instance.com" in graphiti_mcp_url):
            logger.info("ℹ️ Skipping default Graphiti MCP server (not configured)")
        else:
            logger.info(f"🔌 Adding default Graphiti MCP server: {graphiti_mcp_url}")
            graphiti_server = mcp.MCPServerHTTP(
                url=graphiti_mcp_url, 
                timeout=30.0,
                sse_read_timeout=300.0,
            )
            # Ensure server is initialized so tool discovery works reliably
            try:
                await graphiti_server.initialize()
            except Exception as init_e:
                logger.warning(f"⚠️ Failed to initialize Graphiti MCP server: {init_e}")
            mcp_servers.append(graphiti_server)
            logger.info(f"✅ Added default Graphiti MCP server: {graphiti_mcp_url}")
            logger.info(f"📊 Total MCP servers after Graphiti addition: {len(mcp_servers)}")
            
            # Best-effort connectivity check without blocking on SSE stream
            try:
                import aiohttp
                async with aiohttp.ClientSession() as _sess:
                    async with _sess.get(graphiti_mcp_url, headers={"Accept": "text/event-stream"}) as resp:
                        logger.info(f"🔧 Graphiti MCP probe status: {resp.status}")
            except Exception as test_e:
                logger.warning(f"⚠️ Graphiti MCP probe failed: {test_e}")
    except Exception as e:
        logger.error(f"❌ Failed to add default Graphiti MCP server: {e}", exc_info=True)
    
    try:
        # Load MCP servers from the database manager directly to include auth config
        logger.info("🔄 Loading MCP servers from database manager...")
        try:
            from config.mcp_config_db import mcp_manager as db_mcp_manager
            await db_mcp_manager.initialize()
            db_servers = db_mcp_manager.list_servers()
            available_servers = {sid: cfg.to_dict() for sid, cfg in db_servers.items()}
            logger.info(f"✅ Loaded {len(available_servers)} servers from database")
        except Exception as db_error:
            logger.warning(f"⚠️ Database load failed ({db_error}), falling back to JSON config file")
            # Fallback to local config file  
            config_path = '/app/config/mcp_servers.json'
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                available_servers = config.get('servers', {})
                logger.info(f"✅ Loaded {len(available_servers)} servers from JSON config")
            except FileNotFoundError:
                logger.warning("⚠️ mcp_servers.json not found, no servers loaded from config")
                available_servers = {}
        
        logger.info(f"🔍 Looking for MCP servers: {mcp_server_ids}")
        server_names = list(available_servers.keys())
        logger.info(f"🔍 Available MCP servers: {server_names}")
        
        for server_id in mcp_server_ids:
            server_config = available_servers.get(server_id)
            if not server_config:
                logger.warning(f"⚠️ MCP server '{server_id}' not found - available: {server_names}")
                continue
                
            if not server_config.get('enabled', False):
                logger.info(f"ℹ️ MCP server '{server_id}' is disabled, skipping")
                continue
                
            server_type = server_config.get('server_type', '').lower()
            if server_type in ['sse', 'http']:
                url = server_config.get('url')
                if not url:
                    logger.warning(f"⚠️ No URL for server '{server_id}', skipping")
                    continue
                
                # Substitute environment variables in URL
                if url.startswith('${') and url.endswith('}'):
                    env_var = url[2:-1]  # Remove ${ and }
                    url = os.getenv(env_var, url)
                    logger.info(f"🔧 Substituted environment variable {env_var} in URL for server '{server_id}': {url}")
                
                try:
                    # Build headers for authentication
                    headers = {}
                    auth = server_config.get('auth', {})
                    if auth and auth.get('type') == 'bearer' and auth.get('token'):
                        headers['Authorization'] = f"Bearer {auth['token']}"
                    
                    logger.info(f"🔌 Connecting to MCP server '{server_id}': {url}")
                    
                    # Create LiveKit MCP server with robust SSE timeouts
                    server = mcp.MCPServerHTTP(
                        url=url,
                        headers=headers if headers else None,
                        timeout=30.0,  # Connection timeout
                        sse_read_timeout=300.0,  # SSE stream can be idle for long periods
                        client_session_timeout_seconds=120.0,  # Keep client session alive longer
                    )
                    # Initialize; tolerate initial SSE idle/read timeouts
                    try:
                        await server.initialize()
                    except Exception as init_e:
                        logger.warning(f"⚠️ Initialize warning for MCP server '{server_id}': {init_e}")
                    mcp_servers.append(server)
                    logger.info(f"✅ Added MCP server: {server_config.get('name', server_id)} ({url})")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create MCP server '{server_id}': {e}")
            else:
                logger.warning(f"⚠️ Server type '{server_type}' not supported for '{server_id}'")
                
    except FileNotFoundError:
        logger.warning("⚠️ mcp_servers.json not found")
    except Exception as e:
        logger.error(f"❌ Error loading MCP servers for preset: {e}")
    
    logger.info(f"🎯 Total MCP servers loaded: {len(mcp_servers)}")
    return mcp_servers


async def get_preset_for_room(ctx: JobContext) -> AgentPresetConfig:
    """Get the appropriate preset for a room based on room name or user participant metadata"""
    
    preset_id = None
    
    # Extract preset_id from room name (primary method)
    try:
        room_name = ctx.room.name
        logger.info(f"🔍 Extracting preset from room name: {room_name}")
        
        # Check if room name contains preset info: room--preset-{preset_id}
        if '--preset-' in room_name:
            preset_id = room_name.split('--preset-')[1]
            logger.info(f"✅ Found preset_id in room name: {preset_id}")
        else:
            logger.info("ℹ️ No preset_id found in room name, will use default")
            
    except Exception as e:
        logger.warning(f"❌ Could not extract preset_id from room name: {e}")
    
    logger.info(f"🎯 Using preset_id: {preset_id}")
    
    try:
        # Initialize database and preset manager
        await init_db()
        
        # If we have a preset_id from the room name, try to load that specific preset
        if preset_id:
            try:
                logger.info(f"🔍 Attempting to load preset: {preset_id}")
                specific_preset = await preset_manager.get_preset(preset_id)
                
                if specific_preset and specific_preset.enabled:
                    logger.info(f"✅ Using requested preset: {specific_preset.name}")
                    return specific_preset
                else:
                    logger.warning(f"⚠️ Requested preset '{preset_id}' not found or disabled, falling back to default")
            except Exception as e:
                logger.warning(f"❌ Error loading requested preset '{preset_id}': {e}")
        
        # Try to get default preset
        logger.info("🔍 Attempting to load default preset")
        default_preset = await preset_manager.get_default_preset()
        if default_preset:
            logger.info(f"✅ Using default preset: {default_preset.name}")
            return default_preset
        
        # If no default, get any enabled preset
        logger.info("🔍 No default preset, looking for any enabled preset")
        enabled_presets = await preset_manager.list_enabled_presets()
        if enabled_presets:
            preset = enabled_presets[0]
            logger.info(f"✅ Using first enabled preset: {preset.name}")
            return preset
        
        # Create defaults if none exist
        logger.info("🔍 No presets found, creating defaults...")
        await preset_manager.create_default_presets()
        default_preset = await preset_manager.get_default_preset()
        if default_preset:
            logger.info(f"✅ Using newly created default preset: {default_preset.name}")
            return default_preset
            
    except Exception as e:
        logger.error(f"❌ Error loading preset: {e}")
    
    # Ultimate fallback - create a basic preset in memory
    from agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig
    
    logger.warning("⚠️ Using fallback preset configuration")
    return AgentPresetConfig(
        id="fallback",
        name="Fallback Assistant",
        system_prompt="You are a helpful AI assistant.",
        voice_config=VoiceConfig(provider="openai", voice="alloy"),
        llm_config=LLMConfig(provider="openai", model="gpt-4o-mini"),
        stt_config=STTConfig(provider="deepgram"),
        agent_config=AgentConfig(),
        mcp_server_ids=[],
        enabled=True
    )


async def entrypoint(ctx: JobContext):
    """MINIMAL TEST ENTRYPOINT"""
    logging.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    logging.critical("!!!!!!!!!! MINIMAL ENTRYPOINT CALLED !!!!!!!!!!")
    logging.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    # Attach room info to all structured logs
    ctx.log_context_fields = {"room": ctx.room.name}

    # ---------------------------------------------------------------------
    # 1. Load preset configuration (required for the rest of the flow)
    # ---------------------------------------------------------------------
    logger.info("🔄 Loading preset configuration for room '%s'…", ctx.room.name)
    preset = await get_preset_for_room(ctx)
    logger.info("✅ Using preset '%s'", preset.name)

    # ---------------------------------------------------------------------
    # 2. Check model compatibility (with caching to reduce startup time)
    # ---------------------------------------------------------------------
    tools_disabled = False
    try:
        from utils.model_compatibility import should_disable_tools
        tools_disabled = await should_disable_tools(preset.llm_config.model, preset.llm_config.provider)
        if tools_disabled:
            logger.warning(f"🔧 Tools disabled for {preset.llm_config.model} - running in voice-only mode")
    except Exception as e:
        logger.warning(f"Could not check tool compatibility: {e}")

    # ---------------------------------------------------------------------
    # 3. Asynchronously initialize AI components for efficiency
    # ---------------------------------------------------------------------
    logger.info("Initializing AI components...")
    try:
        # Load MCP servers based on the preset configuration
        mcp_servers_future = asyncio.create_task(
            load_mcp_servers_for_preset(preset.mcp_server_ids)
        )

        # Create tasks for each component to run in parallel
        vad_future = asyncio.create_task(
            load_vad_model(ctx)
        )
        tts_future = asyncio.create_task(
            create_tts_from_config(preset.voice_config)
        )
        llm_future = asyncio.create_task(
            create_llm_from_config(preset.llm_config)
        )

        # Wait for all tasks to complete
        vad, tts, llm, mcp_servers = await asyncio.gather(
            vad_future, tts_future, llm_future, mcp_servers_future
        )

        # Create STT (doesn't require async initialization)
        stt = create_stt_from_config(preset.stt_config)

        # Check for tool compatibility if tools are used
        if getattr(llm, 'has_tools', False) and mcp_servers:
            # Tool compatibility check removed - not needed for current implementation
            pass
        
    except Exception as e:
        logger.error(f"Failed to initialize AI components: {e}", exc_info=True)
        # We can also add a shutdown hook here if needed
        return

    # Handle tools_disabled case conservatively: if we have MCP servers configured
    # (e.g., Graphiti Memory), keep them so the agent can still use tools via MCP.
    if tools_disabled and not mcp_servers:
        logger.warning("🔧 Tools disabled for this model and no MCP servers configured")
    elif mcp_servers:
        logger.info("✅ Loaded %s MCP server(s) for preset", len(mcp_servers))
        for i, server in enumerate(mcp_servers):
            server_info = f"  - MCP Server {i+1}: {type(server).__name__}"
            if hasattr(server, 'url'):
                server_info += f" ({server.url})"
            logger.info(server_info)
    else:
        logger.warning("⚠️ No MCP servers configured – agent will only have built-in function tools")

    # ---------------------------------------------------------------------
    # 4. Configure session options efficiently
    # ---------------------------------------------------------------------
    speed = preset.agent_config.speed_config or SpeedConfig()

    # Choose turn-detection implementation with proper fallbacks  
    # Temporarily force VAD to avoid turn detector model issues
    turn_detection_impl = "vad"
    logger.info("🔧 Using VAD turn detection (multilingual model temporarily disabled)")
    # try:
    #     turn_detection_impl = (
    #         MultilingualModel() if (speed.advanced_turn_detection and MULTILINGUAL_AVAILABLE and MultilingualModel) else "vad"
    #     )
    # except Exception as e:
    #     logger.warning(f"Turn detection model failed to load: {e}, falling back to VAD")
    #     turn_detection_impl = "vad"

    # ---------------------------------------------------------------------
    # 5. Create the LiveKit AgentSession with optimized settings
    # ---------------------------------------------------------------------
    session = AgentSession(
        vad=vad,
        stt=stt,
        llm=llm,
        tts=tts,
        turn_detection=turn_detection_impl,
        mcp_servers=mcp_servers or None,
        # Behaviour toggles
        allow_interruptions=preset.agent_config.allow_interruptions,
        preemptive_generation=preset.agent_config.preemptive_generation,
        # Optimized timing for faster responses
        min_interruption_duration=speed.min_interruption_duration,
        min_endpointing_delay=speed.min_endpointing_delay,
        max_endpointing_delay=speed.max_endpointing_delay,
        # Others
        max_tool_steps=preset.agent_config.max_tool_steps,
    )

    # ---------------------------------------------------------------------
    # 6. Wire up enhanced metrics logging with latency tracking
    # ---------------------------------------------------------------------
    usage_collector = metrics.UsageCollector()
    last_eou_metrics: metrics.EOUMetrics | None = None

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        nonlocal last_eou_metrics
        
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)
        
        # Track end-of-utterance metrics for latency monitoring
        if ev.metrics.type == "eou_metrics":
            last_eou_metrics = ev.metrics
            logger.debug(f"📊 EOU detected - speech_id: {ev.metrics.speech_id}")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev):
        # Log end-to-end latency when agent starts speaking
        try:
            if (
                ev.new_state == "speaking"
                and last_eou_metrics
                and hasattr(session, 'current_speech')
                and session.current_speech
                and hasattr(session.current_speech, 'id')
                and last_eou_metrics.speech_id == session.current_speech.id
            ):
                latency = ev.created_at - last_eou_metrics.last_speaking_time
                logger.info(f"⚡ End-to-end latency: {latency:.3f}s")
        except Exception as e:
            logger.debug(f"Error logging latency metrics: {e}")

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info("📊 Usage for preset '%s': %s", preset.name, summary)
        
        # Log performance statistics
        prewarm_time = ctx.proc.userdata.get("prewarm_timestamp")
        if prewarm_time:
            total_time = time.time() - prewarm_time
            logger.info(f"⏱️  Total session time: {total_time:.1f}s")

    ctx.add_shutdown_callback(log_usage)

    # ---------------------------------------------------------------------
    # 7. Start the agent with optimized settings
    # ---------------------------------------------------------------------
    agent = DynamicAgent(preset, ctx_room=ctx.room)
    # NOTE: Do NOT manually set the `session` attribute; it is a read-only
    # property provided by the LiveKit `Agent` base class once the agent is
    # started via `session.start()`. Attempting to override it raises an
    # AttributeError and crashes the worker. Helper methods that need the
    # session should access `self.session` after the agent is running.
    
    # CRITICAL: Connect to the room context BEFORE starting the session
    logger.info("🔌 Connecting to room context...")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info("✅ Room context connected")
    
    # Configure room input options
    room_input_options = RoomInputOptions()
    if noise_cancellation:
        room_input_options.noise_cancellation = noise_cancellation.BVC()
    
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=room_input_options,
    )

    logger.info("🚀 Session started with preset '%s'", preset.name)

    # Test: Send a startup event to verify the communication channel
    logger.info("🧪 Testing communication channel with startup event...")
    try:
        agent._emit_memory_event("memory-startup", "Agent initialized successfully")
        logger.info("✅ Startup event sent successfully")
    except Exception as e:
        logger.error(f"❌ Failed to send startup event: {e}")

    # ---------------------------------------------------------------
    # Register event hooks *after* the session has started.  The
    # current event types (function_tools_executed) are only emitted
    # once the agent is running, so it's safe to attach the listener
    # at this point without missing any events.
    # ---------------------------------------------------------------

    @session.on("function_tools_executed")
    def _on_function_tools_executed(ev):  # noqa: D401
        """Forward tool-execution events to the front-end."""
        logger.info(f"🔥 function_tools_executed event fired! Event: {ev}")
        logger.info(f"🔍 Function calls in event: {ev.function_calls}")
        
        try:
            for fnc_call in ev.function_calls:
                logger.info(f"🔧 Processing function call: {fnc_call}, name: {getattr(fnc_call, 'name', 'unknown')}")
                logger.info(f"🏠 Agent has _emit_tool_event: {hasattr(agent, '_emit_tool_event')}")
                if hasattr(agent, "_emit_tool_event"):
                    logger.info(f"✅ Calling agent._emit_tool_event for: {getattr(fnc_call, 'name', 'tool')}")
                    agent._emit_tool_event(getattr(fnc_call, "name", "tool"))
                else:
                    logger.info(f"❌ Agent missing _emit_tool_event method")
        except Exception as e:  # pragma: no cover
            logger.error(f"💥 Error emitting tool event: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

def prewarm_process(proc):
    """Enhanced prewarm function for optimal performance"""
    logger.info("🔧 Prewarming agent components...")
    
    # Configure VAD with optimized settings for better speech detection
    proc.userdata["vad"] = silero.VAD.load(
        # Minimum speech duration to consider as actual speech (prevents noise triggering)
        min_speech_duration=0.2,
        # Minimum silence duration before considering speech ended
        min_silence_duration=0.5,
        # Speech probability threshold (0.5 = balanced, higher = more strict)
        activation_threshold=0.5,
    )
    logger.info("✅ VAD model loaded and configured")
    
    # Prewarm audio processing if librosa is available
    if LIBROSA_AVAILABLE:
        try:
            # Warmup the librosa JIT compilation with a sample audio
            sample_audio = np.random.randn(16000).astype(np.float32)  # 1 second of audio
            librosa.effects.time_stretch(sample_audio, rate=1.2)
            logger.info("✅ Audio processing (librosa) prewarmed")
        except Exception as e:
            logger.warning(f"Failed to prewarm audio processing: {e}")
    
    # Store initialization timestamp for performance tracking
    proc.userdata["prewarm_timestamp"] = time.time()
    logger.info("🚀 Agent prewarming complete")

if __name__ == "__main__":
    from livekit.agents import cli, WorkerOptions
    import sys
    
    # Handle download-files command for Docker build
    if len(sys.argv) > 1 and sys.argv[1] == "download-files":
        logger.info("🔄 Pre-downloading required model files...")
        try:
            # Import and initialize voice recognition models
            from livekit.plugins import silero
            # Use the supported Silero API to load (and thus download) the VAD model
            silero.VAD.load()
            logger.info("✅ VAD model downloaded")
            
            # Download turn detection models if available (disabled for now)
            # if MULTILINGUAL_AVAILABLE:
            #     try:
            #         MultilingualModel()._download()
            #         logger.info("✅ Turn detection models downloaded")
            #     except Exception as e:
            #         logger.warning(f"Turn detection model download failed: {e}")
            
            logger.info("✅ Model download complete")
        except Exception as e:
            logger.error(f"❌ Model download failed: {e}")
            sys.exit(1)
    else:
        # Normal agent startup
        cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint)) 