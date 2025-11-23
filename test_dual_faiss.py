"""
Test script for dual FAISS implementation
Tests memory caching, validation, and retrieval priority
"""

import asyncio
from coordinator import Coordinator
from mcp_servers.multiMCP import MultiMCP

async def test_dual_faiss():
    """Test the dual FAISS implementation"""
    
    print("=" * 80)
    print("DUAL FAISS IMPLEMENTATION TEST")
    print("=" * 80)
    
    # Initialize system
    multi_mcp = MultiMCP()
    await multi_mcp.initialize()
    coordinator = Coordinator(multi_mcp)
    
    # Test 1: Fresh query (should use documents)
    print("\n\n" + "=" * 80)
    print("TEST 1: Fresh Query (Should use documents)")
    print("=" * 80)
    query1 = "What is the cost of a 3888 sqft Camelia apartment?"
    result1 = await coordinator.run(query1)
    print(f"\nResult: {result1}")
    
    # Test 2: Same query again (should use memory cache if high confidence)
    print("\n\n" + "=" * 80)
    print("TEST 2: Repeat Query (Should use memory cache if previous was high confidence)")
    print("=" * 80)
    result2 = await coordinator.run(query1)
    print(f"\nResult: {result2}")
    
    # Test 3: Query with freshness keyword (should bypass cache)
    print("\n\n" + "=" * 80)
    print("TEST 3: Query with 'current' keyword (Should bypass cache)")
    print("=" * 80)
    query3 = "What is the current cost of a 3888 sqft Camelia apartment?"
    result3 = await coordinator.run(query3)
    print(f"\nResult: {result3}")
    
    print("\n\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_dual_faiss())
