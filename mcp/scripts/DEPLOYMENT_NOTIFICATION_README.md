# Deployment Notification Integration

This document explains how to integrate the Slack notification system with your MCP deployment workflow.

## Overview

When your MCP tool (like `deploy_watcher`) completes and returns a JSON status with `workflow_status: "COMPLETE"` and `alarm_status: "SUCCESS"`, you update the job's `status` field to `"complete"` in DynamoDB. The async monitor will detect completed deployment jobs and automatically send a Slack notification.

## Workflow

1. **MCP Tool Output**: Your tool outputs JSON like:
   ```json
   {"workflow_status": "COMPLETE", "alarm_status": "SUCCESS"}
   ```

2. **Update DynamoDB**: When you get COMPLETE + SUCCESS, update the job's `status` to `"complete"`
3. **Automatic Notification**: The async monitor polls every 10 seconds and sends Slack notifications for completed deployment jobs

## Usage

### Option 1: Using the Helper Script

After your MCP tool completes, run:

```bash
# Using JSON string
./update_deployment_status.py <job_id> --json '{"workflow_status": "COMPLETE", "alarm_status": "SUCCESS"}'

# Or using individual arguments
./update_deployment_status.py <job_id> --workflow-status COMPLETE --alarm-status SUCCESS
```

### Option 2: Integrate in Your Workflow

In your deployment script or MCP tool:

```python
from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor

# After deployment completes
monitor = AsyncTaskMonitor()
monitor.update_task(job_id, {
    "workflow_status": "COMPLETE",
    "alarm_status": "SUCCESS"
})
```

### Option 3: From Command Line

You can pipe the MCP tool output directly:

```bash
# Example with q chat
q chat --no-interactive --trust-all-tools << EOF | python -c "
import sys, json
from awslabs.cloudwatch_appsignals_mcp_server.async_monitor import AsyncTaskMonitor
data = json.loads(sys.stdin.read())
monitor = AsyncTaskMonitor()
monitor.update_task('$JOB_ID', data)
"
This prompt is for follow-up task of deploy_helper MCP tool...
EOF
```

## Testing

To test the integration:

```bash
# Run the test script
./test_deployment_notification.py
```

This will:
1. Create a test job in DynamoDB
2. Update it with COMPLETE/SUCCESS status
3. Start the async monitor
4. Send a Slack notification within 10-15 seconds

## Configuration

Make sure the following environment variable is set:
- `SLACK_WEBHOOK_URL`: Your Slack webhook URL

The async monitor needs to be running for notifications to be sent. It polls DynamoDB every 10 seconds for deployment status updates.

## Notification Messages

- **Success**: "🎉 Deployment Successful! The deployment was successful and your memory usage has decreased back to normal levels."
- **Failure**: "⚠️ Deployment Failed! The deployment completed but the alarm condition was not resolved."