#!/usr/bin/env python3
"""Test the complete deployment workflow as the LLM would use it."""

import sys
import os
import asyncio
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from awslabs.cloudwatch_appsignals_mcp_server.server import register_event, update_event
from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor


async def simulate_deployment_workflow():
    """Simulate the complete deployment workflow."""
    print("=== Simulating Complete Deployment Workflow ===\n")
    
    # Step 1: Simulate deploy_helper returning a commit SHA
    # Use a more unique prefix to avoid collisions
    commit_sha = f"test{datetime.now().strftime('%H%M%S')}_{datetime.now().microsecond}abcdef1234567890"
    print("Step 1: deploy_helper completed")
    print(f"  Commit SHA: {commit_sha}")
    print(f"  Job ID will be: {commit_sha[:8]}\n")
    
    # Step 2: Register the deployment event
    prompt = """This prompt is for follow-up task of deploy_helper MCP tool. There are several tasks to do:
    - call deploy_watcher MCP tool
    - format output of deploy_watcher MCP tool as json string like below.
      {"workflow_status": "PENDING" or "COMPLETE", "alarm_status": "SUCCESS" or "FAILURE"}"""
    
    print("Step 2: Calling register_event...")
    result = await register_event(prompt=prompt, id=commit_sha)
    print(result)
    print()
    
    # Step 3: Simulate deploy_watcher returning success after deployment
    print("Step 3: deploy_watcher monitoring deployment...")
    await asyncio.sleep(2)  # Simulate deployment time
    
    deployment_result = {
        "workflow_status": "COMPLETE",
        "alarm_status": "SUCCESS"
    }
    print(f"  Deploy watcher result: {json.dumps(deployment_result)}\n")
    
    # Step 4: Update the event based on deployment result
    print("Step 4: Calling update_event...")
    result = await update_event(
        job_id=commit_sha[:8],  # Use first 8 chars as per MCP tool behavior
        workflow_status=deployment_result["workflow_status"],
        alarm_status=deployment_result["alarm_status"]
    )
    print(result)
    
    return commit_sha[:8]


async def main():
    """Main function."""
    # Load Slack webhook
    env_file = os.path.join(os.path.dirname(__file__), '../../slackbot/.env')
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key == 'SLACK_WEBHOOK_URL':
                        os.environ['SLACK_WEBHOOK_URL'] = value
    
    # Run the deployment workflow
    job_id = await simulate_deployment_workflow()
    
    # Start async monitor
    print("\n" + "="*50)
    print("Step 5: Starting async monitor for Slack notifications...")
    monitor = AsyncTaskMonitor()
    monitor.start()
    
    print(f"\nMonitoring job {job_id}")
    print("Slack notification should arrive within 10-15 seconds...")
    print("\nWaiting 20 seconds...")
    
    await asyncio.sleep(20)
    
    monitor.stop()
    print("\n✅ Workflow test complete!")
    print(f"📱 Check Slack for notification about job: {job_id}")


if __name__ == '__main__':
    asyncio.run(main())