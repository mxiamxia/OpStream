#!/usr/bin/env python3
"""Test the LLM investigation with actual Amazon Q CLI."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def test_with_amazon_q():
    """Test using real Amazon Q CLI."""
    
    print("Testing LLM investigation with Amazon Q CLI...\n")
    
    # Check if Amazon Q is installed
    import subprocess
    try:
        result = subprocess.run(['q', '--version'], capture_output=True, text=True)
        print(f"✓ Amazon Q CLI found: {result.stdout.strip()}")
    except:
        print("❌ Amazon Q CLI not found")
        print("Install with: brew install amazon-q")
        return
    
    # Enable real LLM
    os.environ['USE_REAL_LLM'] = 'true'
    os.environ['LLM_CLI'] = 'q'
    
    # Create monitor
    monitor = AsyncTaskMonitor(
        region='us-east-1',
        table_name='appsignals-async-jobs'
    )
    
    try:
        # Start the monitor
        monitor.start()
        print("✓ Monitor started\n")
        
        # Create a simple test investigation
        investigation_id = monitor.create_investigation(
            question="What causes high CPU usage in web applications?",
            initial_context={
                'service': 'test-web-app',
                'symptom': 'CPU at 95%',
                'duration': '30 minutes'
            }
        )
        print(f"✓ Created investigation: {investigation_id}")
        
        # Get the investigation
        investigation = monitor.get_task(investigation_id)
        if investigation:
            import re
            prompt = investigation.get('prompt', investigation.get('context', ''))
            question_match = re.search(r'Question: (.+?)\n', prompt)
            question = question_match.group(1) if question_match else 'No question found'
            print(f"  Question: {question}")
        
        # Wait for one polling cycle
        print("\nWaiting 65 seconds for LLM investigation...")
        await asyncio.sleep(65)
        
        # Check results
        investigation = monitor.get_task(investigation_id)
        if investigation:
            prompt = investigation.get('prompt', investigation.get('context', ''))
            status = investigation['status']
            
            # Count iterations
            iterations = len(re.findall(r'--- \d{4}-\d{2}-\d{2}T', prompt))
            
            print(f"\n✓ After LLM call:")
            print(f"  Status: {status}")
            print(f"  Iterations: {iterations}")
            
            # Show latest findings
            findings = re.findall(r'Findings:\n((?:- .+\n)+)', prompt)
            if findings:
                print("\n  Latest Findings:")
                latest_findings = findings[-1].strip().split('\n')
                for finding in latest_findings:
                    print(f"  {finding}")
            
            if status == 'complete':
                answer_match = re.search(r'Answer: (.+?)\n', prompt)
                if answer_match:
                    print(f"\n  Final answer: {answer_match.group(1)}")
        
        # Clean up - stop the investigation
        monitor.stop_task(investigation_id)
        print(f"\n✓ Stopped investigation")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        monitor.stop()
        print("✓ Monitor stopped")
    
    print("\nTest completed!")


async def test_direct_llm_call():
    """Test calling LLM directly to see the response format."""
    
    print("\n" + "="*80)
    print("Testing direct LLM call to see response format...\n")
    
    monitor = AsyncTaskMonitor(region='us-east-1')
    
    # Build a test prompt with current context string format
    test_context = """Question: Why is the API returning 503 errors?

Created: 2024-01-01T10:00:00.000000

Initial Context:
- service: api-gateway
- symptoms: 503 errors
- frequency: intermittent

Investigation Log:

--- 2024-01-01T10:01:00.000000 ---
Status: continuing
Action: Started investigation
Findings:
- service_status: running
- memory_usage: 85%

--- 2024-01-01T10:02:00.000000 ---
Status: continuing  
Action: Checked service health
Findings:
- connection_pool: exhausted
- active_connections: 95"""
    
    prompt = monitor._build_investigation_prompt(test_context)
    
    print("Prompt being sent to LLM:")
    print("-" * 40)
    print(prompt)
    print("-" * 40)
    
    # Enable real LLM for this test
    os.environ['USE_REAL_LLM'] = 'true'
    
    try:
        # Call LLM directly
        response = await monitor._call_llm_cli(prompt)
        print("\nParsed response:")
        print(f"Status: {response['status']}")
        print(f"Action: {response['action']}")
        print(f"Findings: {response['findings']}")
        if 'answer' in response:
            print(f"Answer: {response['answer']}")
    except Exception as e:
        print(f"\nDirect LLM call failed: {e}")
        print("This is expected if Amazon Q is not installed or configured")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run both tests
    asyncio.run(test_with_amazon_q())
    asyncio.run(test_direct_llm_call())