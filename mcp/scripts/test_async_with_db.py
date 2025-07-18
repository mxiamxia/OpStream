#!/usr/bin/env python3
"""Test the async monitor with DynamoDB integration."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def test_async_monitor_with_db():
    """Test the async monitor with DynamoDB."""

    print('Testing AsyncTaskMonitor with DynamoDB...')

    # Create monitor (make sure your DynamoDB table exists)
    # You might need to adjust region/table name
    monitor = AsyncTaskMonitor(region='us-east-1', table_name='appsignals-async-jobs')

    try:
        # Start the monitor
        monitor.start()
        print('✓ Monitor started')

        # Create a test investigation
        job_id = monitor.create_investigation(
            question='Why is my test-service experiencing performance issues?',
            initial_context={
                'service': 'test-service',
                'region': 'us-east-1',
                'timeframe': 'last_hour',
                'config': {
                    'check_interval_seconds': 30,
                    'error_threshold': 5.0,
                    'latency_threshold_ms': 1000,
                },
            },
        )
        print(f'✓ Created investigation: {job_id}')

        # Get the investigation
        task = monitor.get_task(job_id)
        if task:
            print(f'✓ Retrieved investigation:')
            print(f'  Status: {task["status"]}')
            print(f'  Question: {task["context"]["question"]}')
            print(f'  Created: {task["context"]["created_at"]}')

        # Wait to see some monitoring checks
        print('\nWaiting 65 seconds to see first investigation iteration...')
        await asyncio.sleep(65)

        # Get updated investigation
        task = monitor.get_task(job_id)
        if task:
            print(f'\n✓ Investigation after first iteration:')
            print(f'  Status: {task["status"]}')
            print(f'  Iterations: {task["context"].get("iteration_count", 0)}')
            print(f'  History entries: {len(task["context"].get("investigation_history", []))}')

        # Stop the investigation
        if monitor.stop_task(job_id):
            print(f'\n✓ Stopped investigation {job_id}')

        # Check final status
        task = monitor.get_task(job_id)
        print(f'  Final status: {task["status"]}')

        # Show findings if available
        if task and task['context'].get('findings'):
            print('\n  Current findings:')
            for key, value in task['context']['findings'].items():
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

    logging.basicConfig(level=logging.INFO)

    # Note: Make sure you have created the DynamoDB table first!
    # You can create it with:
    # aws dynamodb create-table \
    #   --table-name appsignals-async-jobs \
    #   --attribute-definitions AttributeName=job_id,AttributeType=S \
    #   --key-schema AttributeName=job_id,KeyType=HASH \
    #   --billing-mode PAY_PER_REQUEST

    asyncio.run(test_async_monitor_with_db())
