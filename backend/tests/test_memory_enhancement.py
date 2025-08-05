#!/usr/bin/env python3
"""
Memory Enhancement Test Script

Tests the enhanced memory functionality to ensure contextual recall works
as expected for natural conversation scenarios.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.dynamic_agent import DynamicAgent
from core.agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("memory-test")

class MockSession:
    """Mock session for testing memory functionality"""
    def __init__(self):
        self.llm = MockLLM()
        self.room = None

class MockLLM:
    """Mock LLM for testing"""
    def __init__(self):
        self.system_prompt = ""

class MockMessage:
    """Mock message for testing"""
    def __init__(self, text_content: str):
        self.text_content = text_content

class MockChatContext:
    """Mock chat context for testing"""
    pass

def create_test_preset():
    """Create a test preset for the DynamicAgent"""
    return AgentPresetConfig(
        id="test-memory-agent",
        name="Test Memory Agent",
        description="Agent for testing enhanced memory functionality",
        system_prompt="You are a helpful assistant with memory capabilities.",
        voice_config=VoiceConfig(provider="openai", voice="ash"),
        llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.7),
        stt_config=STTConfig(provider="deepgram", model="nova-3"),
        agent_config=AgentConfig(allow_interruptions=True),
        mcp_server_ids=[]
    )

async def test_memory_scenarios():
    """Test various memory scenarios to validate enhanced functionality"""
    
    print("🧠 Testing Enhanced Memory Functionality")
    print("=" * 50)
    
    # Initialize the enhanced agent
    preset = create_test_preset()
    agent = DynamicAgent(preset)
    agent.session = MockSession()
    
    # Test scenarios that should trigger memory storage
    print("\n📝 Testing Memory Storage Scenarios")
    print("-" * 30)
    
    storage_scenarios = [
        "I have a golden retriever named Max who is 3 years old",
        "I work at Google as a software engineer",
        "I prefer Italian food over Chinese food",
        "My project is called Project Phoenix and it's about AI assistants",
        "I live in San Francisco and I love hiking"
    ]
    
    for scenario in storage_scenarios:
        print(f"Input: {scenario}")
        is_worthy = agent.is_memory_worthy(scenario)
        print(f"Memory worthy: {is_worthy}")
        
        if is_worthy:
            await agent.store_memory(scenario, f"Test Memory - {datetime.now().strftime('%H:%M:%S')}")
        print()
    
    # Wait a moment for storage to complete
    await asyncio.sleep(2)
    
    # Test scenarios that should trigger memory retrieval
    print("\n🔍 Testing Memory Retrieval Scenarios")
    print("-" * 30)
    
    retrieval_scenarios = [
        "What kind of dog food should I get?",  # Should find info about golden retriever
        "Can you recommend a good restaurant?",  # Should find Italian food preference
        "What programming languages should I learn for my career?",  # Should find Google/software engineer info
        "How should I name my new app?",  # Should find Project Phoenix reference
        "What outdoor activities would I enjoy?",  # Should find hiking preference
        "Tell me about my dog",  # Explicit memory trigger
        "What do you know about my work?"  # Explicit memory trigger
    ]
    
    for scenario in retrieval_scenarios:
        print(f"Query: {scenario}")
        
        # Test keyword extraction
        keywords = agent.extract_search_keywords(scenario)
        print(f"Extracted keywords: {keywords[:5]}")  # Show first 5
        
        # Test memory retrieval
        memories = await agent.retrieve_contextual_memory(scenario)
        print(f"Retrieved memories: {len(memories)}")
        
        if memories:
            for i, memory in enumerate(memories, 1):
                print(f"  {i}. {memory[:100]}{'...' if len(memory) > 100 else ''}")
        else:
            print("  No relevant memories found")
        
        print()
    
    print("\n✅ Memory Enhancement Test Complete")

async def test_keyword_extraction():
    """Test the keyword extraction functionality"""
    print("\n🔤 Testing Keyword Extraction")
    print("-" * 30)
    
    preset = create_test_preset()
    agent = DynamicAgent(preset)
    
    test_cases = [
        "What kind of dog food should I get?",
        "Can you recommend a good Italian restaurant in San Francisco?",
        "I need advice on my software engineering career",
        "What outdoor activities would be fun for hiking lovers?",
        "Tell me about the best project management tools"
    ]
    
    for case in test_cases:
        keywords = agent.extract_search_keywords(case)
        print(f"Input: {case}")
        print(f"Keywords: {keywords}")
        print()

async def test_memory_triggers():
    """Test memory trigger detection"""
    print("\n🎯 Testing Memory Triggers")
    print("-" * 30)
    
    preset = create_test_preset()
    agent = DynamicAgent(preset)
    
    # Test explicit memory triggers
    explicit_triggers = [
        "Do you remember what I told you about my dog?",
        "What do you know about my work?",
        "Tell me about my previous conversations",
        "Recall what I said earlier"
    ]
    
    # Test memory worthy content
    memory_worthy = [
        "I have a cat named Whiskers",
        "I work at Microsoft",
        "I prefer tea over coffee",
        "My hobby is photography"
    ]
    
    # Test non-triggers
    non_triggers = [
        "What's the weather like?",
        "How do I cook pasta?",
        "What time is it?",
        "Can you help me with math?"
    ]
    
    print("Explicit memory triggers:")
    for trigger in explicit_triggers:
        result = agent.is_explicit_memory_trigger(trigger)
        print(f"  '{trigger}' -> {result}")
    
    print("\nMemory worthy content:")
    for worthy in memory_worthy:
        result = agent.is_memory_worthy(worthy)
        print(f"  '{worthy}' -> {result}")
    
    print("\nNon-memory related queries:")
    for non_trigger in non_triggers:
        explicit = agent.is_explicit_memory_trigger(non_trigger)
        worthy = agent.is_memory_worthy(non_trigger)
        print(f"  '{non_trigger}' -> Explicit: {explicit}, Worthy: {worthy}")

async def main():
    """Run all memory tests"""
    try:
        await test_keyword_extraction()
        await test_memory_triggers()
        await test_memory_scenarios()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 