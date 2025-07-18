#!/usr/bin/env python3
"""Test the basic scheduler functionality."""

import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def test_scheduler():
    """Test the basic scheduler functionality."""

    print('Testing AsyncTaskMonitor...')

    # Create and start monitor
    monitor = AsyncTaskMonitor()
    monitor.start()
    print('✓ Monitor started')

    # Let it run for a bit to see the test job execute
    print('Waiting 65 seconds to see scheduled jobs run (job runs every 30s)...')
    print('You should see log messages from the test job...')

    await asyncio.sleep(65)

    # Stop monitor
    monitor.stop()
    print('✓ Monitor stopped')

    print('\nTest completed!')


if __name__ == '__main__':
    # Set up logging to see the output
    import logging

    logging.basicConfig(level=logging.INFO)

    asyncio.run(test_scheduler())
