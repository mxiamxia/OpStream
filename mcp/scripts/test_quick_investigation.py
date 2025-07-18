#!/usr/bin/env python3
"""Quick test of the LLM investigation workflow."""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def test_quick_investigation():
    """Test the LLM investigation with shorter wait times."""
    
    print("Testing LLM-driven investigation (quick version)...")
    
    # Create monitor
    monitor = AsyncTaskMonitor(
        region='us-east-1',
        table_name='appsignals-async-jobs'
    )
    
    try:
        # Start the monitor
        monitor.start()
        print("✓ Monitor started with master polling")
        
        # Create an investigation
        investigation_id = monitor.create_investigation(
            question="What is causing 5xx errors in the API gateway?",
            initial_context={
                'service': 'api-gateway',
                'error_code': '503',
                'frequency': 'intermittent',
                'started': '2 hours ago'
            }
        )
        print(f"✓ Created investigation: {investigation_id}")
        
        # Check initial state
        investigation = monitor.get_task(investigation_id)
        if investigation:
            prompt = investigation.get('prompt', investigation.get('context', ''))
            # Extract question from prompt string
            import re
            question_match = re.search(r'Question: (.+?)\n', prompt)
            question = question_match.group(1) if question_match else 'No question found'
            
            print(f"\nInitial state:")
            print(f"  Question: {question}")
            print(f"  Status: {investigation['status']}")
        
        # Wait for multiple polling cycles
        print("\nWaiting for investigation to progress...")
        for i in range(4):  # 4 minutes to see completion
            await asyncio.sleep(60)
            
            investigation = monitor.get_task(investigation_id)
            if investigation:
                status = investigation['status']
                prompt = investigation.get('prompt', investigation.get('context', ''))
                
                # Count iterations by counting timestamp entries
                iterations = len(re.findall(r'--- \d{4}-\d{2}-\d{2}T', prompt))
                
                print(f"\nAfter {i+1} minute(s):")
                print(f"  Status: {status}")
                print(f"  Iterations: {iterations}")
                
                # Show latest findings
                findings = re.findall(r'Findings:\n((?:- .+\n)+)', prompt)
                if findings:
                    print("  Latest Findings:")
                    latest_findings = findings[-1].strip().split('\n')
                    for finding in latest_findings:
                        print(f"  {finding}")
                
                if status == 'complete':
                    print(f"\n✓ Investigation completed!")
                    # Extract answer
                    answer_match = re.search(r'Answer: (.+?)\n', prompt)
                    if answer_match:
                        print(f"  Final answer: {answer_match.group(1)}")
                    break
        
        # Show investigation timeline
        if investigation:
            prompt = investigation.get('prompt', investigation.get('context', ''))
            timestamps = re.findall(r'--- (\d{4}-\d{2}-\d{2}T[\d:.]+) ---', prompt)
            if timestamps:
                print(f"\nInvestigation timeline ({len(timestamps)} iterations):")
                for i, timestamp in enumerate(timestamps, 1):
                    print(f"  - Iteration {i}: {timestamp}")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop monitor
        monitor.stop()
        print("\n✓ Monitor stopped")
    
    print("\nTest completed!")


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(test_quick_investigation())