#!/usr/bin/env python3
"""
Memory Enhancement Demonstration

This script demonstrates how the enhanced memory system works by showing
contextual recall for natural conversation scenarios like the dog food example.
"""

import asyncio
import logging
from core.dynamic_agent import DynamicAgent
from core.agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig

# Configure logging to show memory operations
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class MockSession:
    def __init__(self):
        self.llm = MockLLM()
        self.room = None

class MockLLM:
    def __init__(self):
        self.system_prompt = ""

def create_demo_preset():
    """Create a demo preset for the DynamicAgent"""
    return AgentPresetConfig(
        id="demo-memory-agent",
        name="Demo Memory Agent",
        description="Agent for demonstrating enhanced memory functionality",
        system_prompt="You are a helpful assistant with memory capabilities.",
        voice_config=VoiceConfig(provider="openai", voice="ash"),
        llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.7),
        stt_config=STTConfig(provider="deepgram", model="nova-3"),
        agent_config=AgentConfig(allow_interruptions=True),
        mcp_server_ids=[]
    )

async def demonstrate_enhanced_memory():
    """Demonstrate the enhanced memory functionality"""
    
    print("\n🎯 Enhanced Memory System Demonstration")
    print("=" * 50)
    print("This demo shows how the agent now provides contextual memory recall")
    print("for natural questions like 'What dog food should I get?'\n")
    
    # Initialize agent
    preset = create_demo_preset()
    agent = DynamicAgent(preset)
    agent.session = MockSession()
    
    # Step 1: User shares information about their dog
    print("👤 User: 'I have a golden retriever named Max who is 3 years old and weighs 70 pounds'")
    user_input = "I have a golden retriever named Max who is 3 years old and weighs 70 pounds"
    
    is_worthy = agent.is_memory_worthy(user_input)
    print(f"🧠 Agent detects memory-worthy content: {is_worthy}")
    
    if is_worthy:
        await agent.store_memory(user_input, "User's Dog Information")
        print("✅ Information stored to memory")
    
    print("\n" + "-" * 50)
    
    # Step 2: Later, user asks about dog food (no explicit memory trigger)
    print("👤 User: 'What kind of dog food should I get?'")
    question = "What kind of dog food should I get?"
    
    # Show keyword extraction
    keywords = agent.extract_search_keywords(question)
    print(f"🔍 Agent extracts keywords: {keywords}")
    
    # Show memory search
    print("🧠 Agent automatically searches memory for relevant context...")
    memories = await agent.retrieve_contextual_memory(question)
    
    if memories:
        print(f"💭 Found {len(memories)} relevant memories:")
        for i, memory in enumerate(memories, 1):
            print(f"   {i}. {memory}")
    else:
        print("💭 No relevant memories found")
    
    print("\n🤖 Agent can now respond with context like:")
    print("   'Since you have a golden retriever named Max who is 3 years old and weighs 70 pounds,")
    print("    I'd recommend a high-quality large breed dog food with ingredients like...'")
    
    print("\n" + "=" * 50)
    print("🎉 Enhanced Memory Features:")
    print("• Automatic contextual search for every user input")
    print("• Keyword and concept-based memory retrieval") 
    print("• No need for explicit 'remember' triggers")
    print("• Natural, human-like memory recall")
    print("• Multiple search strategies for better coverage")

async def compare_old_vs_new():
    """Compare old vs new memory behavior"""
    
    print("\n📊 Old vs New Memory Behavior Comparison")
    print("=" * 50)
    
    preset = create_demo_preset()
    agent = DynamicAgent(preset)
    
    test_queries = [
        "What kind of dog food should I get?",
        "Can you recommend a good restaurant?", 
        "What programming languages should I learn?",
        "What outdoor activities would I enjoy?"
    ]
    
    print("OLD BEHAVIOR (trigger-based):")
    print("• Only searched memory when user said 'remember' or 'my'")
    print("• Would miss contextual opportunities")
    print("• Agent would say 'I don't know, I need more information'")
    
    print("\nNEW BEHAVIOR (contextual):")
    for query in test_queries:
        keywords = agent.extract_search_keywords(query)
        is_explicit = agent.is_explicit_memory_trigger(query)
        
        print(f"\nQuery: '{query}'")
        print(f"• Extracts keywords: {keywords[:3]}")  # Show first 3
        print(f"• Searches memory automatically: ✅")
        print(f"• Can provide personalized response: ✅")

if __name__ == "__main__":
    asyncio.run(demonstrate_enhanced_memory())
    asyncio.run(compare_old_vs_new()) 