#!/usr/bin/env python3
"""
Test script to verify MCP client fixes for hanging issues
"""

import asyncio
import sys
import os
import time
from datetime import datetime

# Add the orchestrator module to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orchestrator'))

from orchestrator.taco_search_client import taco_search_client


async def test_concurrent_requests():
    """Test multiple concurrent requests to check for hanging issues"""
    print("🧪 Testing concurrent MCP requests...")
    
    # Test queries
    test_queries = [
        "tacos",
        "steak tacos", 
        "al pastor",
        "downtown austin",
        "spicy tacos"
    ]
    
    start_time = time.time()
    
    # Create concurrent tasks
    tasks = []
    for i, query in enumerate(test_queries):
        task = asyncio.create_task(
            test_single_request(f"Request-{i+1}", query)
        )
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n📊 Test Results:")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Requests: {len(test_queries)}")
    print(f"Average time per request: {total_time/len(test_queries):.2f} seconds")
    
    # Analyze results
    successful = 0
    failed = 0
    fallback_used = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ Request {i+1}: Exception - {result}")
            failed += 1
        elif result and result.get('success'):
            if result.get('data', {}).get('source') == 'static_fallback':
                print(f"🔄 Request {i+1}: Success (fallback used)")
                fallback_used += 1
            else:
                print(f"✅ Request {i+1}: Success (MCP server)")
                successful += 1
        else:
            print(f"❌ Request {i+1}: Failed")
            failed += 1
    
    print(f"\n📈 Summary:")
    print(f"Successful (MCP): {successful}")
    print(f"Successful (fallback): {fallback_used}")
    print(f"Failed: {failed}")
    
    # Test circuit breaker state
    cb_state = taco_search_client.circuit_breaker.state.value
    cb_failures = taco_search_client.circuit_breaker.failure_count
    print(f"Circuit breaker state: {cb_state}")
    print(f"Circuit breaker failures: {cb_failures}")


async def test_single_request(request_id: str, query: str):
    """Test a single request with timeout"""
    print(f"🔵 {request_id}: Starting search for '{query}'")
    start_time = time.time()
    
    try:
        # Test with timeout
        result = await asyncio.wait_for(
            taco_search_client.search_tacos(query, limit=5, session_id=request_id),
            timeout=30.0  # 30 second timeout
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        if result.success:
            source = result.data.get('source', 'unknown')
            print(f"✅ {request_id}: Completed in {duration:.2f}s (source: {source})")
            return {'success': True, 'duration': duration, 'data': result.data}
        else:
            print(f"❌ {request_id}: Failed in {duration:.2f}s - {result.error}")
            return {'success': False, 'duration': duration, 'error': result.error}
            
    except asyncio.TimeoutError:
        print(f"⏰ {request_id}: Timeout after 30 seconds")
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        print(f"💥 {request_id}: Exception after {duration:.2f}s - {e}")
        return {'success': False, 'duration': duration, 'error': str(e)}


async def test_circuit_breaker():
    """Test circuit breaker functionality"""
    print("\n🔧 Testing circuit breaker functionality...")
    
    # Force some failures to test circuit breaker
    print("Forcing failures to test circuit breaker...")
    
    # Simulate failures by calling with invalid method
    for i in range(4):  # Should trigger circuit breaker after 3 failures
        try:
            # This should fail and trigger circuit breaker
            await taco_search_client.send_mcp_request("invalid_method", {})
        except:
            pass
        
        cb_state = taco_search_client.circuit_breaker.state.value
        cb_failures = taco_search_client.circuit_breaker.failure_count
        print(f"Attempt {i+1}: Circuit breaker state: {cb_state}, failures: {cb_failures}")
    
    # Now try a normal request - should use fallback
    print("\nTesting fallback when circuit breaker is open...")
    result = await taco_search_client.search_tacos("test query", session_id="circuit-test")
    
    if result.success and result.data.get('source') == 'static_fallback':
        print("✅ Circuit breaker working - fallback used successfully")
    else:
        print("❌ Circuit breaker not working as expected")


async def main():
    """Main test function"""
    print("🚀 Starting MCP Client Hanging Issues Test")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)
    
    try:
        # Test concurrent requests
        await test_concurrent_requests()
        
        # Test circuit breaker
        await test_circuit_breaker()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\n🧹 Cleaning up...")
        await taco_search_client.close()


if __name__ == "__main__":
    asyncio.run(main())
