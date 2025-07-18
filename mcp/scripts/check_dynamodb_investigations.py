#!/usr/bin/env python3
"""Check if DynamoDB table exists and list existing investigations."""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import json
import re


def check_table_exists(region, table_name):
    """Check if the DynamoDB table exists."""
    dynamodb = boto3.client('dynamodb', region_name=region)

    try:
        response = dynamodb.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        print(f"✓ Table '{table_name}' exists in {region}")
        print(f'  Status: {table_status}')
        print(f'  Item count: {response["Table"].get("ItemCount", "Unknown")}')
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"❌ Table '{table_name}' does not exist in {region}")
            print('\nTo create the table, run:')
            print(f'aws dynamodb create-table \\')
            print(f'  --table-name {table_name} \\')
            print(f'  --attribute-definitions AttributeName=job_id,AttributeType=S \\')
            print(f'  --key-schema AttributeName=job_id,KeyType=HASH \\')
            print(f'  --billing-mode PAY_PER_REQUEST \\')
            print(f'  --region {region}')
            return False
        else:
            print(f'❌ Error checking table: {e}')
            return False


def list_investigations(region, table_name):
    """List all investigations in the table."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)

    try:
        # Scan the table for all items
        response = table.scan()
        items = response.get('Items', [])

        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))

        if not items:
            print('\nNo investigations found in the table.')
            return

        # Separate investigations from other job types
        investigations = []
        other_jobs = []

        for item in items:
            prompt = item.get('prompt', item.get('context', ''))  # Support both old and new field names
            if isinstance(prompt, str) and 'Question:' in prompt:  # This is an investigation
                investigations.append(item)
            else:
                other_jobs.append(item)

        # Display investigations
        if investigations:
            print(f'\nFound {len(investigations)} investigation(s):')
            print('-' * 80)

            for inv in sorted(
                investigations,
                key=lambda x: x.get('job_id', ''),
                reverse=True,
            ):
                job_id = inv.get('job_id', 'Unknown')
                status = inv.get('status', 'Unknown')
                prompt = inv.get('prompt', inv.get('context', ''))  # Support both old and new field names
                
                # Extract question from prompt string
                question_match = re.search(r'Question: (.+?)\n', prompt)
                question = question_match.group(1) if question_match else 'No question found'
                
                # Extract created date
                created_match = re.search(r'Created: (.+?)\n', prompt)
                created_at = created_match.group(1) if created_match else 'Unknown'
                
                # Count iterations by counting timestamp entries
                iterations = len(re.findall(r'--- \d{4}-\d{2}-\d{2}T', prompt))

                # Extract updated timestamp from DynamoDB
                updated_at = inv.get('updated_at', 'Unknown')
                
                print(f'\nInvestigation ID: {job_id}')
                print(f'  Status: {status}')
                print(f'  Question: {question}')
                print(f'  Created: {created_at}')
                print(f'  Updated: {updated_at}')
                print(f'  Iterations: {iterations}')

                # Show latest findings if available
                findings = re.findall(r'Findings:\n((?:- .+\n)+)', prompt)
                if findings:
                    print('  Latest Findings:')
                    latest_findings = findings[-1].strip().split('\n')
                    for finding in latest_findings:
                        print(f'  {finding}')

                # Show answer if completed
                answer_match = re.search(r'Answer: (.+?)\n', prompt)
                if status == 'complete' and answer_match:
                    answer = answer_match.group(1)
                    print(f'  Final Answer: {answer[:200]}...')

        # Display other jobs
        if other_jobs:
            print(f'\n\nFound {len(other_jobs)} other job(s):')
            print('-' * 80)

            for job in sorted(
                other_jobs, key=lambda x: x.get('context', {}).get('created_at', ''), reverse=True
            ):
                job_id = job.get('job_id', 'Unknown')
                status = job.get('status', 'Unknown')
                prompt = job.get('prompt', job.get('context', {}))
                # For legacy jobs, try to extract from prompt string or use defaults
                if isinstance(prompt, str):
                    created_match = re.search(r'Created: (.+?)\n', prompt)
                    created_at = created_match.group(1) if created_match else 'Unknown'
                    service_name = 'legacy-job'
                else:
                    created_at = prompt.get('created_at', 'Unknown') if isinstance(prompt, dict) else 'Unknown'
                    service_name = prompt.get('service_name', 'Unknown') if isinstance(prompt, dict) else 'Unknown'

                print(f'\nJob ID: {job_id}')
                print(f'  Status: {status}')
                print(f'  Service: {service_name}')
                print(f'  Created: {created_at}')

    except Exception as e:
        print(f'\n❌ Error listing investigations: {e}')
        import traceback

        traceback.print_exc()


def main():
    """Main function."""
    # Configuration
    REGION = 'us-east-1'
    TABLE_NAME = 'appsignals-async-jobs'

    print(f'Checking DynamoDB table and investigations...')
    print(f'Region: {REGION}')
    print(f'Table: {TABLE_NAME}')
    print('=' * 80)

    # Check if table exists
    if check_table_exists(REGION, TABLE_NAME):
        # List investigations
        list_investigations(REGION, TABLE_NAME)

    print('\n' + '=' * 80)
    print('Check completed!')


if __name__ == '__main__':
    main()
