#!/usr/bin/env python3
"""Test the LLM-driven investigation workflow."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def test_llm_investigation():
    """Test the LLM-driven investigation workflow."""

    print('Testing LLM-driven investigation workflow...')

    # Create monitor
    monitor = AsyncTaskMonitor(region='us-east-1', table_name='appsignals-async-jobs')

    try:
        # Check if DynamoDB table exists first
        try:
            # Test connection by trying to get a non-existent item
            monitor.get_task('test-connection')
            print('✓ Connected to DynamoDB table')
        except Exception as e:
            print(f'❌ Failed to connect to DynamoDB: {e}')
            print("  Make sure the table 'appsignals-async-jobs' exists in us-east-1")
            print('  Run: aws dynamodb create-table \\')
            print('       --table-name appsignals-async-jobs \\')
            print('       --attribute-definitions AttributeName=job_id,AttributeType=S \\')
            print('       --key-schema AttributeName=job_id,KeyType=HASH \\')
            print('       --billing-mode PAY_PER_REQUEST')
            return

        # Start the monitor
        monitor.start()
        print('✓ Monitor started with master polling')

        # Create an investigation
        investigation_id = monitor.create_investigation(
            question='Why is my deployment experiencing high latency?',
            initial_context={
                'service': 'api-gateway',
                'region': 'us-east-1',
                'timeframe': 'last_hour',
                'symptoms': ['high p99 latency', '5xx errors'],
            },
        )
        print(f'✓ Created investigation: {investigation_id}')

        # Get initial state
        investigation = monitor.get_task(investigation_id)
        if investigation:
            print(f'\n✓ Investigation created:')
            print(f'  Question: {investigation["context"]["question"]}')
            print(f'  Status: {investigation["status"]}')
            print(f'  Created: {investigation["context"]["created_at"]}')

        # Wait for master poller to process (runs every 60 seconds)
        print('\nWaiting 65 seconds for first polling cycle...')
        await asyncio.sleep(65)

        # Check progress
        investigation = monitor.get_task(investigation_id)
        if investigation:
            print(f'\n✓ After first poll:')
            print(f'  Status: {investigation["status"]}')
            print(f'  Iterations: {investigation["context"]["iteration_count"]}')
            print(f'  History entries: {len(investigation["context"]["investigation_history"])}')

            if investigation['context']['findings']:
                print('  Current findings:')
                for key, value in investigation['context']['findings'].items():
                    print(f'    - {key}: {value}')

        # Wait for more polling cycles (simulation completes after 3 iterations)
        print('\nWaiting 180 seconds for investigation to complete...')
        await asyncio.sleep(180)

        # Check final state
        investigation = monitor.get_task(investigation_id)
        if investigation:
            print(f'\n✓ Final investigation state:')
            print(f'  Status: {investigation["status"]}')
            print(f'  Total iterations: {investigation["context"]["iteration_count"]}')

            if investigation['status'] == 'completed':
                print(
                    f'  Final answer: {investigation["context"].get("final_answer", "No answer")}'
                )
                print('\n  Investigation history:')
                for entry in investigation['context']['investigation_history']:
                    print(f'    - Iteration {entry["iteration"]}: {entry["action"]}')

                print('\n  Final findings:')
                for key, value in investigation['context']['findings'].items():
                    print(f'    - {key}: {value}')

    except Exception as e:
        print(f'\n❌ Error: {e}')
        import traceback

        traceback.print_exc()
    finally:
        # Stop monitor
        monitor.stop()
        print('\n✓ Monitor stopped')

    print('\nTest completed!')


if __name__ == '__main__':
    # Set up logging to see the output
    import logging

    logging.basicConfig(
        level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        asyncio.run(test_llm_investigation())
    except KeyboardInterrupt:
        print('\n\nTest interrupted by user')
    except Exception as e:
        print(f'\n\nFatal error: {e}')
        import traceback

        traceback.print_exc()
