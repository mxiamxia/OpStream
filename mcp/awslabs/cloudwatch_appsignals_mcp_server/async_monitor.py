import asyncio
import threading
import uuid
import boto3
import os
import aiohttp
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger


def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


class AsyncTaskMonitor:
    """Manages background async monitoring tasks."""

    def __init__(self, region: str = 'us-east-1', table_name: str = 'appsignals-async-jobs'):
        """Initialize the async task monitor."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.scheduler: Optional[AsyncIOScheduler] = None

        # DynamoDB setup
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

        # In-memory cache of active tasks for quick access
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

        logger.info(f'AsyncTaskMonitor initialized with table {table_name} in region {region}')

    def start(self):
        """Start the background monitoring thread and scheduler."""
        if self.thread and self.thread.is_alive():
            logger.warning('AsyncTaskMonitor already running')
            return

        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

        import time

        time.sleep(0.5)

        logger.info('AsyncTaskMonitor started')

    def stop(self):
        """Stop the background monitoring thread."""
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(self._stop_loop(), self.loop)

        if self.thread:
            self.thread.join(timeout=5)

        logger.info('AsyncTaskMonitor stopped')

    def _run_event_loop(self):
        """Run the event loop in the background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.loop.run_until_complete(self._init_scheduler())

        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    async def _init_scheduler(self):
        """Initialize the scheduler in the event loop."""
        self.scheduler = AsyncIOScheduler()

        # Master polling job that runs every 60 seconds
        self.scheduler.add_job(
            self._poll_active_investigations,
            'interval',
            seconds=60,
            id='master_poller',
            replace_existing=True,
        )
        
        # Deployment status polling job that runs every 10 seconds
        self.scheduler.add_job(
            self._poll_deployment_status,
            'interval',
            seconds=10,
            id='deployment_poller',
            replace_existing=True,
        )

        self.scheduler.start()
        logger.debug('Scheduler initialized with master polling job and deployment poller')

    async def _stop_loop(self):
        """Stop the event loop gracefully."""
        if self.scheduler:
            self.scheduler.shutdown()

        self.loop.stop()

    async def _poll_active_investigations(self):
        """Master polling job that checks all active investigations."""
        logger.info(f'Master poller running at {datetime.now()}')

        # Scan DynamoDB for all active jobs
        try:
            response = self.table.scan(
                FilterExpression='#s = :open',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':open': 'open'},
            )

            open_jobs = response.get('Items', [])
            logger.info(f'Found {len(open_jobs)} open investigations')

            # Process each open job
            for job in open_jobs:
                job_id = job['job_id']
                await self._process_investigation(job_id, job)

        except Exception as e:
            logger.error(f'Error in master polling: {e}')
    
    async def _poll_deployment_status(self):
        """Poll for completed deployment jobs and send notifications."""
        logger.debug(f'Deployment poller running at {datetime.now()}')
        
        try:
            # Scan for completed jobs
            response = self.table.scan(
                FilterExpression='#s = :complete',
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':complete': 'complete'},
            )
            
            items = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    FilterExpression='#s = :complete',
                    ExpressionAttributeNames={'#s': 'status'},
                    ExpressionAttributeValues={':complete': 'complete'},
                )
                items.extend(response.get('Items', []))
            
            # Check for deployment-related jobs
            for item in items:
                job_id = item.get('job_id', '')
                
                # Check if this is a deployment job (has deployment_id in context or prompt)
                prompt = item.get('prompt', '')
                is_deployment = False
                
                if isinstance(prompt, str):
                    # Check if this is a deployment-related job
                    is_deployment = any(term in prompt.lower() for term in ['deployment', 'deploy', 'alarm'])
                
                if is_deployment:
                    # Check if we've already notified for this job
                    notified_key = f'notified_{job_id}'
                    if not hasattr(self, '_notified_jobs'):
                        self._notified_jobs = set()
                    
                    if notified_key not in self._notified_jobs:
                        # Send Slack notification
                        message = (
                            "🎉 *Deployment Successful!* 🎉\n\n"
                            "The deployment was successful and your memory usage has decreased back to normal levels."
                        )
                        await self.send_slack_notification(message, job_id)
                        
                        # Mark as notified
                        self._notified_jobs.add(notified_key)
                        logger.info(f"Sent Slack notification for successful deployment job {job_id}")
            
        except Exception as e:
            logger.error(f'Error in deployment polling: {e}')

    def create_investigation(
        self, question: str, initial_context: Dict[str, Any], job_id: Optional[str] = None
    ) -> str:
        """Create a new investigation task for LLM-driven analysis."""
        if not job_id:
            job_id = f'investigation-{uuid.uuid4()}'

        # Simplified schema - context is just a string
        context_text = f"Question: {question}\n\nCreated: {datetime.utcnow().isoformat()}\n\nInitial Context:\n"
        for key, value in initial_context.items():
            context_text += f"- {key}: {value}\n"
        context_text += "\nInvestigation Log:\n"

        item = {
            'job_id': job_id,
            'status': 'open',
            'prompt': context_text,
            'updated_at': datetime.utcnow().isoformat(),
        }

        # Convert floats to Decimal for DynamoDB
        item_for_db = convert_floats_to_decimal(item)
        self.table.put_item(Item=item_for_db)

        # Also store in memory for quick access
        self.active_tasks[job_id] = item

        logger.info(f'Created investigation {job_id} for question: {question}')
        return job_id

    def get_task(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a task using minimal schema."""
        try:
            response = self.table.get_item(Key={'job_id': job_id})
            if 'Item' in response:
                # Update memory cache
                self.active_tasks[job_id] = response['Item']
                return response['Item']
            return None
        except Exception as e:
            logger.error(f'Error retrieving job {job_id}: {e}')
            return None

    def update_task(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update a task in DynamoDB."""
        try:
            # Get current task
            task = self.get_task(job_id)
            if not task:
                return False

            # Update fields directly (simplified schema)
            if 'status' in updates:
                task['status'] = updates['status']
            
            if 'prompt' in updates:
                task['prompt'] = updates['prompt']  # Replace entire prompt string
            
            # Always update the timestamp
            task['updated_at'] = datetime.utcnow().isoformat()

            # Save to DynamoDB (convert floats to Decimal)
            task_for_db = convert_floats_to_decimal(task)
            self.table.put_item(Item=task_for_db)

            # Update memory cache
            self.active_tasks[job_id] = task

            return True
        except Exception as e:
            logger.error(f'Error updating job {job_id}: {e}')
            return False

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get all active tasks from memory cache (for performance).

        Note: For a full implementation, you might want to scan DynamoDB
        periodically to sync the cache, but for now we'll use the in-memory cache.
        """
        return [task for task in self.active_tasks.values() if task.get('status') == 'open']

    def stop_task(self, job_id: str) -> bool:
        """Stop monitoring a specific task."""
        return self.update_task(job_id, {'status': 'complete'})
    
    async def send_slack_notification(self, message: str, job_id: str = None):
        """Send notification to Slack webhook."""
        webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
        if not webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
            return
        
        payload = {
            "text": message,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        }
        
        if job_id:
            payload["blocks"].append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Job ID: `{job_id}`"
                    }
                ]
            })
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent successfully for job {job_id}")
                    else:
                        logger.error(f"Failed to send Slack notification: {response.status}")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    async def _process_investigation(self, job_id: str, job_data: Dict[str, Any]):
        """Process a single investigation by feeding context to LLM."""
        try:
            logger.info(f'Processing investigation {job_id}')

            # Get the current prompt (which is just a string)
            current_prompt = job_data.get('prompt', '')

            # Build prompt by adding instructions to the current prompt
            prompt = self._build_investigation_prompt(current_prompt)

            # Call LLM
            llm_response = await self._simulate_llm_investigation(job_id, prompt, 0)

            # Update investigation with LLM response
            await self._update_investigation(job_id, llm_response, current_prompt)

        except Exception as e:
            logger.error(f'Error processing investigation {job_id}: {e}')

    def _build_investigation_prompt(self, current_context: str) -> str:
        """Build a prompt for the LLM using the current context string."""
        prompt = current_context + "\n\n" + """
You are an expert system administrator investigating this issue. Based on the context above:

1. If you have enough information to identify the root cause and solution, provide your final conclusion and recommendations.

2. If you need more information, describe what specific steps you would take next to continue the investigation.

3. Include any metrics, findings, or observations that are relevant to understanding the issue.

Be specific and actionable in your response. Focus on practical troubleshooting steps and measurable findings.
"""
        return prompt

    async def _simulate_llm_investigation(
        self, job_id: str, prompt: str, iteration: int
    ) -> Dict[str, Any]:
        """Call LLM for investigation or use simulation."""
        # Check if we should use real LLM
        use_real_llm = os.environ.get('USE_REAL_LLM', 'false').lower() == 'true'
        
        if use_real_llm:
            try:
                return await self._call_llm_cli(prompt)
            except Exception as e:
                logger.error(f"LLM call failed: {e}. Falling back to simulation.")
        
        # Simulation for testing with proper tokens
        if iteration < 3:
            # Simulate continuing investigation
            simulated_response = f"""[STATUS:CONTINUING]
[ACTION:Analyzing metrics for iteration {iteration + 1}]
[FINDING:metric_{iteration}=value_{iteration}]
[FINDING:progress={(iteration + 1) * 33}%]

Based on the current findings, I need to continue gathering more data to identify the root cause."""
        else:
            # Simulate completion
            simulated_response = """[STATUS:COMPLETE]
[ACTION:Investigation complete - root cause identified]
[FINDING:root_cause=High latency detected in service X]
[FINDING:recommendation=Scale up instances]
[FINDING:confidence=85%]
[ANSWER:The deployment issue is caused by high latency in service X. Recommend scaling up instances.]

The investigation has identified that service X is experiencing high latency under load."""
        
        return self._parse_llm_response(simulated_response)
    
    async def _call_llm_cli(self, prompt: str) -> Dict[str, Any]:
        """Call Amazon Q or other LLM CLI and parse response."""
        import subprocess
        
        # Determine which CLI to use
        llm_cli = os.environ.get('LLM_CLI', 'q')
        
        # Build command based on CLI type
        if llm_cli == 'q':
            # Amazon Q CLI - pass prompt as direct argument
            cmd = ['q', 'chat', prompt]
        else:
            # Generic CLI fallback
            cmd = [llm_cli, prompt]
        
        logger.info(f"Calling LLM CLI: {llm_cli}")
        
        try:
            # Run the command
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                error_msg = stderr.decode() if stderr else 'Unknown error'
                raise Exception(f"LLM CLI failed: {error_msg}")
            
            # Get the response
            response_text = stdout.decode().strip()
            
            # Parse the response using our token-based approach
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Error calling LLM CLI: {e}")
            raise
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse natural language LLM response and extract structured information."""
        import re
        
        result = {
            'status': 'continuing',  # default
            'action': 'Analyzing investigation',
            'findings': {},
            'next_steps': ''
        }
        
        # First try to find our tokens if the LLM used them
        status_match = re.search(r'\[STATUS:(CONTINUING|COMPLETE)\]', response_text)
        if status_match:
            status = status_match.group(1).lower()
            result['status'] = 'complete' if status == 'complete' else 'continuing'
        else:
            # Parse natural language for completion indicators
            completion_indicators = [
                'investigation complete', 'analysis complete', 'concluded', 'final answer',
                'root cause identified', 'solution found', 'issue resolved', 'recommend',
                'in conclusion', 'the cause is', 'the problem is'
            ]
            
            response_lower = response_text.lower()
            if any(indicator in response_lower for indicator in completion_indicators):
                result['status'] = 'complete'
        
        # Extract action from tokens or natural language
        action_match = re.search(r'\[ACTION:([^\]]+)\]', response_text)
        if action_match:
            result['action'] = action_match.group(1).strip()
        else:
            # Extract action from natural language
            # Look for sentences that describe what the LLM is doing
            action_patterns = [
                r'I (?:will|am|need to|should) ([^.]+)',
                r'Next(?:,)? I will ([^.]+)',
                r'(?:Let me|I\'ll) ([^.]+)',
                r'The next step is to ([^.]+)',
                r'I recommend ([^.]+)'
            ]
            
            for pattern in action_patterns:
                match = re.search(pattern, response_text, re.IGNORECASE)
                if match:
                    result['action'] = match.group(1).strip()
                    break
        
        # Extract findings from tokens or natural language
        finding_matches = re.findall(r'\[FINDING:([^=]+)=([^\]]+)\]', response_text)
        for key, value in finding_matches:
            result['findings'][key.strip()] = value.strip()
        
        # If no token findings, extract from natural language
        if not result['findings']:
            # Look for patterns like "CPU usage is 85%", "error rate: 5%", etc.
            metric_patterns = [
                r'(\w+(?:\s+\w+)*)\s+(?:is|at|shows?|indicates?)\s+(\d+(?:\.\d+)?%?(?:ms|MB|GB)?)',
                r'(\w+(?:\s+\w+)*):?\s+(\d+(?:\.\d+)?%?(?:ms|MB|GB)?)',
                r'(\w+(?:\s+\w+)*)\s+of\s+(\d+(?:\.\d+)?%?(?:ms|MB|GB)?)'
            ]
            
            for pattern in metric_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                for metric, value in matches:
                    clean_metric = metric.strip().lower().replace(' ', '_')
                    result['findings'][clean_metric] = value.strip()
        
        # Extract answer if status is complete
        if result['status'] == 'complete':
            answer_match = re.search(r'\[ANSWER:([^\]]+)\]', response_text)
            if answer_match:
                result['answer'] = answer_match.group(1).strip()
            else:
                # Try to extract a natural language conclusion
                # Look for conclusive statements
                conclusion_patterns = [
                    r'(?:In conclusion|Therefore|The (?:root )?cause is|The (?:issue|problem) is|This is (?:caused by|due to))[:.]\s*([^.]+)',
                    r'(?:I recommend|The solution is|To fix this)[:.]\s*([^.]+)',
                    r'(?:The investigation shows|Analysis reveals)[:.]\s*([^.]+)'
                ]
                
                for pattern in conclusion_patterns:
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        result['answer'] = match.group(1).strip()
                        break
                
                # If still no answer, use the last sentence as a summary
                if 'answer' not in result:
                    sentences = re.split(r'[.!?]+', response_text.strip())
                    if sentences and len(sentences[-1].strip()) > 10:
                        result['answer'] = sentences[-1].strip()
        
        logger.debug(f"Parsed LLM response: {result}")
        return result

    async def _update_investigation(
        self, job_id: str, llm_response: Dict[str, Any], current_prompt: str
    ):
        """Update investigation based on LLM response."""
        timestamp = datetime.utcnow().isoformat()

        # Get current task
        task = self.get_task(job_id)
        if not task:
            logger.error(f'Task {job_id} not found')
            return

        # Append LLM response to prompt string
        new_context = current_prompt + f"\n\n--- {timestamp} ---\n"
        new_context += f"Status: {llm_response.get('status', 'unknown')}\n"
        new_context += f"Action: {llm_response.get('action', 'Unknown')}\n"

        # Add findings
        if llm_response.get('findings'):
            new_context += "Findings:\n"
            for key, value in llm_response['findings'].items():
                new_context += f"- {key}: {value}\n"

        # Add answer if complete
        if llm_response.get('answer'):
            new_context += f"Answer: {llm_response['answer']}\n"

        # Update status if complete
        new_status = task['status']
        if llm_response.get('status') == 'complete':
            new_status = 'complete'
            logger.info(f'Investigation {job_id} completed')

        # Save updates
        self.update_task(job_id, {'status': new_status, 'prompt': new_context})
