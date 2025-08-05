#!/usr/bin/env python3
"""
Unified Agent Memory Test

Tests the DynamicAgent with integrated memory functionality to ensure
the dog food scenario and other contextual recall works properly.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.dynamic_agent import DynamicAgent
from core.agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("unified-memory-test")

class MockSession:
    """Mock session for testing"""
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
        description="Agent for testing unified memory functionality",
        system_prompt="You are a helpful assistant with memory capabilities.",
        voice_config=VoiceConfig(provider="openai", voice="ash"),
        llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.7),
        stt_config=STTConfig(provider="deepgram", model="nova-3"),
        agent_config=AgentConfig(allow_interruptions=True),
        mcp_server_ids=[]
    )

async def test_unified_memory_functionality():
    """Test the unified DynamicAgent memory functionality"""
    
    print("🔬 Testing Unified DynamicAgent Memory Functionality")
    print("=" * 60)
    
    # Create the unified agent with a test preset
    preset = create_test_preset()
    agent = DynamicAgent(preset)
    agent.session = MockSession()
    
    print(f"✅ Created DynamicAgent with preset: {preset.name}")
    print(f"Agent instructions enhanced with memory: {len(agent.instructions) > len(preset.system_prompt)}")
    print()
    
    # Test 1: Store user information about their dog
    print("📝 Test 1: Storing Dog Information")
    print("-" * 40)
    
    dog_info = "I have a golden retriever named Max who is 3 years old and weighs 70 pounds"
    print(f"User: {dog_info}")
    
    is_worthy = agent.is_memory_worthy(dog_info)
    print(f"Memory worthy: {is_worthy}")
    
    if is_worthy:
        await agent.store_memory(dog_info, "User's Dog Information")
        print("✅ Stored dog information to memory")
    
    print()
    
    # Test 2: The critical dog food question
    print("🐕 Test 2: Dog Food Question (The Critical Test)")
    print("-" * 40)
    
    dog_food_question = "What food should I get for my dog?"
    print(f"User: {dog_food_question}")
    
    # Extract keywords
    keywords = agent.extract_search_keywords(dog_food_question)
    print(f"Extracted keywords: {keywords}")
    
    # Test memory retrieval
    memories = await agent.retrieve_contextual_memory(dog_food_question)
    print(f"Retrieved memories: {len(memories)}")
    
    if memories:
        print("🎯 SUCCESS: Found relevant memories!")
        for i, memory in enumerate(memories, 1):
            print(f"  {i}. {memory}")
    else:
        print("❌ FAILED: No relevant memories found for dog food question")
    
    print()
    
    # Test 3: Work-related question
    print("💼 Test 3: Work Information")
    print("-" * 40)
    
    work_info = "I work at Google as a software engineer"
    print(f"User: {work_info}")
    
    if agent.is_memory_worthy(work_info):
        await agent.store_memory(work_info, "User's Work Information")
        print("✅ Stored work information")
    
    await asyncio.sleep(1)  # Brief pause for storage
    
    work_question = "What programming languages should I learn for my career?"
    print(f"User: {work_question}")
    
    work_memories = await agent.retrieve_contextual_memory(work_question)
    print(f"Retrieved work memories: {len(work_memories)}")
    
    if work_memories:
        print("🎯 SUCCESS: Found work-related memories!")
        for i, memory in enumerate(work_memories, 1):
            print(f"  {i}. {memory}")
    else:
        print("❌ No work memories found")
    
    print()
    
    # Test 4: Memory performance statistics
    print("📊 Test 4: Memory Performance")
    print("-" * 40)
    
    stats = agent.get_memory_stats()
    print(f"Searches performed: {stats['searches_performed']}")
    print(f"Memories retrieved: {stats['memories_retrieved']}")
    print(f"Memories stored: {stats['memories_stored']}")
    print(f"Success rate: {stats['retrieval_success_rate']:.1%}")
    print(f"Average search time: {stats['average_search_time']:.3f}s")
    
    # Test 5: User turn simulation
    print()
    print("🔄 Test 5: Simulated User Turn")
    print("-" * 40)
    
    # Simulate a user turn to test the integration
    mock_context = MockChatContext()
    mock_message = MockMessage("What kind of toys would be good for my dog?")
    
    print(f"Simulating user turn: {mock_message.text_content}")
    
    try:
        await agent.on_user_turn_completed(mock_context, mock_message)
        print("✅ User turn completed successfully")
        print(f"Memory context set: {bool(agent.memory_context)}")
        if agent.memory_context:
            print(f"Context preview: {agent.memory_context[:100]}...")
    except Exception as e:
        print(f"❌ Error in user turn: {e}")
    
    print()
    print("=" * 60)
    print("🎉 Unified Agent Memory Test Complete!")
    
    # Final summary
    final_stats = agent.get_memory_stats()
    print(f"Final Statistics:")
    print(f"  Total searches: {final_stats['searches_performed']}")
    print(f"  Total memories retrieved: {final_stats['memories_retrieved']}")
    print(f"  Total memories stored: {final_stats['memories_stored']}")
    
    return final_stats['searches_performed'] > 0 and final_stats['memories_retrieved'] > 0

async def main():
    """Run the unified memory test"""
    try:
        success = await test_unified_memory_functionality()
        if success:
            print("\n✅ OVERALL TEST: PASSED - Memory system is working!")
        else:
            print("\n❌ OVERALL TEST: FAILED - Memory system needs debugging")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 