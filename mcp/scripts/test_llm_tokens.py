#!/usr/bin/env python3
"""Test the token-based LLM response parsing."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor

def test_token_parsing():
    """Test parsing of different LLM responses with tokens."""
    
    monitor = AsyncTaskMonitor(region='us-east-1')
    
    print("Testing LLM response parsing with tokens...\n")
    
    # Test 1: Continuing investigation
    print("Test 1: Continuing investigation")
    response1 = """[STATUS:CONTINUING]
[ACTION:Analyzing CloudWatch metrics for latency spikes]
[FINDING:p99_latency=2500ms]
[FINDING:error_rate=3.5%]
[FINDING:cpu_usage=45%]

I've found that the p99 latency is quite high at 2500ms. Let me check the database connection pool next."""
    
    result1 = monitor._parse_llm_response(response1)
    print(f"Status: {result1['status']}")
    print(f"Action: {result1['action']}")
    print(f"Findings: {result1['findings']}")
    print("-" * 80)
    
    # Test 2: Complete investigation
    print("\nTest 2: Complete investigation")
    response2 = """[STATUS:COMPLETE]
[ACTION:Root cause identified - database connection exhaustion]
[FINDING:root_cause=Database connection pool exhausted]
[FINDING:max_connections=100]
[FINDING:active_connections=100]
[FINDING:waiting_queries=47]
[ANSWER:The high latency is caused by database connection pool exhaustion. The application has reached the maximum of 100 connections with 47 queries waiting.]

The investigation shows that your database connection pool is exhausted, causing queries to queue up and resulting in high latency."""
    
    result2 = monitor._parse_llm_response(response2)
    print(f"Status: {result2['status']}")
    print(f"Action: {result2['action']}")
    print(f"Findings: {result2['findings']}")
    print(f"Answer: {result2.get('answer', 'N/A')}")
    print("-" * 80)
    
    # Test 3: Response without proper tokens (fallback)
    print("\nTest 3: Response without tokens (should use defaults)")
    response3 = """I think there might be an issue with the load balancer configuration.
Let me investigate further."""
    
    result3 = monitor._parse_llm_response(response3)
    print(f"Status: {result3['status']} (default)")
    print(f"Action: {result3['action']} (default)")
    print(f"Findings: {result3['findings']}")
    print("-" * 80)
    
    # Test 4: Mixed format
    print("\nTest 4: Mixed format with multiple findings")
    response4 = """Looking at the metrics, I can see several issues.

[STATUS:CONTINUING]
[ACTION:Investigating service dependencies]
[FINDING:service_a_latency=500ms]
[FINDING:service_b_latency=1200ms]
[FINDING:service_c_status=healthy]
[FINDING:cache_hit_rate=15%]

The low cache hit rate combined with high service B latency suggests we need to look deeper."""
    
    result4 = monitor._parse_llm_response(response4)
    print(f"Status: {result4['status']}")
    print(f"Action: {result4['action']}")
    print(f"Findings: {json.dumps(result4['findings'], indent=2)}")
    
    print("\nAll tests completed!")

if __name__ == "__main__":
    import json
    test_token_parsing()