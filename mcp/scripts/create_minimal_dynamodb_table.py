#!/usr/bin/env python3
"""Create DynamoDB table with minimal schema for async jobs."""

import boto3
import os
import sys


def create_minimal_async_jobs_table():
    """Create DynamoDB table with minimal schema: job_id, status, context."""

    # Get region from environment or use default
    region = os.environ.get('AWS_REGION', 'us-east-1')

    print(f'Creating DynamoDB table in region: {region}')

    try:
        dynamodb = boto3.resource('dynamodb', region_name=region)

        table_name = 'appsignals-async-jobs'

        # Check if table already exists
        existing_tables = [table.name for table in dynamodb.tables.all()]
        if table_name in existing_tables:
            print(f'Table {table_name} already exists.')
            return

        # Create the table with minimal schema
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'job_id',
                    'KeyType': 'HASH',  # Partition key only
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'job_id',
                    'AttributeType': 'S',  # String
                }
                # Note: We don't define 'status' or 'context' in AttributeDefinitions
                # because they're not used as keys
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
            Tags=[
                {'Key': 'Application', 'Value': 'AppSignals-MCP-Server'},
                {'Key': 'Purpose', 'Value': 'Async-Job-State'},
            ],
        )

        print(f'Creating table {table_name}...')

        # Wait for table to be created
        table.wait_until_exists()

        print(f'✅ Table {table_name} created successfully!')
        print(f'   Schema:')
        print(f'   - job_id: Partition key (String)')
        print(f'   - status: Regular attribute (String)')
        print(f'   - context: Regular attribute (Map/JSON)')
        print(f'   Billing: PAY_PER_REQUEST (on-demand)')

    except Exception as e:
        print(f'❌ Error creating table: {str(e)}')
        sys.exit(1)


if __name__ == '__main__':
    create_minimal_async_jobs_table()
