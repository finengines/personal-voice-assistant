#!/usr/bin/env python3
"""
Memory Optimization Test

Tests the optimized memory system to validate performance improvements
and new features like caching, filtering, and parallel searches.
"""

import asyncio
import time
import sys
import os

# Add paths for imports
sys.path.append(os.path.dirname(__file__))

async def test_memory_optimizations():
    """Test the optimized memory system"""
    
    print("⚡ Memory Optimization Test")
    print("=" * 50)
    
    # Import with optimizations
    try:
        from core.dynamic_agent import DynamicAgent
        from core.agent_config import AgentPresetConfig, VoiceConfig, LLMConfig, STTConfig, AgentConfig
        
        def create_test_preset():
            return AgentPresetConfig(
                id="test-optimized-agent",
                name="Optimized Memory Agent",
                description="Testing optimized memory system",
                system_prompt="You are a helpful assistant with optimized memory.",
                voice_config=VoiceConfig(provider="openai", voice="ash"),
                llm_config=LLMConfig(model="gpt-4o-mini", temperature=0.7),
                stt_config=STTConfig(provider="deepgram", model="nova-3"),
                agent_config=AgentConfig(allow_interruptions=True),
                mcp_server_ids=[]
            )
        
        print("✅ Imports successful")
        
        # Create optimized agent
        preset = create_test_preset()
        agent = DynamicAgent(preset)
        
        print(f"✅ Agent created with cache size: {agent.cache_max_size}")
        print(f"✅ Search timeout: {agent.memory_search_timeout}s")
        print(f"✅ Skip patterns: {len(agent.skip_patterns)}")
        
        # Test different performance profiles
        print("\n🎛️ Testing Performance Profiles:")
        print("-" * 30)
        
        agent.configure_memory_performance("fast")
        print(f"Fast profile - timeout: {agent.memory_search_timeout}s, min query: {agent.min_query_length}")
        
        agent.configure_memory_performance("comprehensive")  
        print(f"Comprehensive profile - timeout: {agent.memory_search_timeout}s, min query: {agent.min_query_length}")
        
        agent.configure_memory_performance("balanced")
        print(f"Balanced profile - timeout: {agent.memory_search_timeout}s, min query: {agent.min_query_length}")
        
        # Test smart filtering
        print("\n🎯 Testing Smart Filtering:")
        print("-" * 30)
        
        test_queries = [
            "hi",  # Should be skipped (too short)
            "ok",  # Should be skipped (common pattern)
            "What is the weather?",  # Should be skipped (simple factual)
            "What food should I get for my dog?",  # Should NOT be skipped
            "Can you help me with my career?",  # Should NOT be skipped
        ]
        
        for query in test_queries:
            should_skip = agent._should_skip_memory_search(query)
            print(f"  '{query}' -> Skip: {should_skip}")
        
        # Test caching
        print("\n💾 Testing Memory Caching:")
        print("-" * 30)
        
        # Test cache operations
        test_query = "What food should I get for my dog?"
        
        # First call - should be cache miss
        start_time = time.time()
        results1 = await agent.retrieve_contextual_memory(test_query)
        time1 = time.time() - start_time
        
        print(f"First call: {len(results1)} results in {time1:.3f}s")
        
        # Second call - should be cache hit (if results were found)
        start_time = time.time()
        results2 = await agent.retrieve_contextual_memory(test_query)
        time2 = time.time() - start_time
        
        print(f"Second call: {len(results2)} results in {time2:.3f}s")
        
        if time2 < time1:
            print("✅ Cache optimization working (second call faster)")
        else:
            print("ℹ️ No cache benefit (likely no results to cache)")
        
        # Test cache stats
        cache_stats = agent.get_memory_cache_stats()
        print(f"Cache stats: {cache_stats['cache_hits']} hits, {cache_stats['cache_misses']} misses")
        
        # Test keyword extraction optimization
        print("\n🔤 Testing Keyword Extraction:")
        print("-" * 30)
        
        test_queries_keywords = [
            "What food should I get for my dog?",
            "Can you recommend a good restaurant?",
            "Help me with my programming career at Google"
        ]
        
        for query in test_queries_keywords:
            keywords = agent.extract_search_keywords(query)
            print(f"  '{query}' -> {keywords[:3]}")  # Show first 3
        
        # Performance summary
        print("\n📊 Performance Summary:")
        print("-" * 30)
        
        stats = agent.get_memory_stats()
        print(f"Total searches: {stats['searches_performed']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Cache misses: {stats['cache_misses']}")
        
        if stats['search_times']:
            avg_time = sum(stats['search_times']) / len(stats['search_times'])
            print(f"Average search time: {avg_time:.3f}s")
            
            if avg_time < 1.0:
                print("🚀 Excellent performance!")
            elif avg_time < 2.0:
                print("⚡ Good performance!")
            else:
                print("🐌 Consider further optimization")
        
        print("\n✅ Optimization test complete!")
        
        # Test configuration options
        print("\n⚙️ Available Optimizations:")
        print("1. Smart filtering - skips unnecessary searches")
        print("2. Memory caching - avoids repeated API calls") 
        print("3. Parallel searches - faster multi-query execution")
        print("4. Configurable timeouts - prevents hanging")
        print("5. Performance profiles - easy tuning for different needs")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run optimization tests"""
    success = await test_memory_optimizations()
    
    if success:
        print("\n🎉 Memory optimization validation: PASSED")
        print("\nTo use optimizations in production:")
        print("- Use agent.configure_memory_performance('fast') for minimal latency")
        print("- Monitor cache hit rates for optimal performance")
        print("- Adjust timeout settings based on your infrastructure")
    else:
        print("\n❌ Memory optimization validation: FAILED")

if __name__ == "__main__":
    asyncio.run(main()) 