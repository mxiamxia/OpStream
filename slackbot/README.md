# AWS Knowledge Base Slack Bot

This Slack bot answers questions based on your AWS knowledge base. It can respond to direct messages and mentions in channels.

## Prerequisites

- Node.js (v12 or higher)
- Slack Workspace with admin privileges
- AWS Account with Bedrock Knowledge Base set up

## Setup Instructions

### 1. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps) and click "Create New App"
2. Choose "From scratch" and give your app a name
3. Select the workspace where you want to install the bot

### 2. Configure Slack App Permissions

1. Navigate to "OAuth & Permissions" in the sidebar
2. Under "Bot Token Scopes", add the following scopes:
   - `app_mentions:read`
   - `channels:history` (to read messages in public channels)
   - `groups:history` (to read messages in private channels)
   - `chat:write`
   - `im:history`
   - `im:read`
   - `im:write`

### 3. Enable Socket Mode

1. Go to "Socket Mode" in the sidebar and enable it
2. Generate an app-level token with the `connections:write` scope
3. Save the token as `SLACK_APP_TOKEN` (starts with `xapp-`)

### 4. Install the App to Your Workspace

1. Go to "Install App" in the sidebar
2. Click "Install to Workspace"
3. Save the Bot User OAuth Token as `SLACK_BOT_TOKEN` (starts with `xoxb-`)

### 5. Get the Signing Secret

1. Go to "Basic Information" in the sidebar
2. Under "App Credentials", copy the "Signing Secret" as `SLACK_SIGNING_SECRET`

### 6. Enable Event Subscriptions

1. Go to "Event Subscriptions" in the sidebar and enable events
2. Under "Subscribe to bot events", add:
   - `app_mention`
   - `message.channels` (for messages in public channels)
   - `message.groups` (for messages in private channels)
   - `message.im` (for direct messages)

### Important: Re-install the App After Permission Changes

After updating permissions and event subscriptions, you must re-install the app to your workspace:
1. Go to "Install App" in the sidebar
2. Click "Reinstall to Workspace" 
3. The new permissions will take effect after reinstallation

### 7. Set Up AWS Credentials

1. In the AWS Management Console, create an IAM user with programmatic access
2. Attach policies for Bedrock Knowledge Bases access
3. Save the access key ID and secret access key

### 8. Configure the Environment Variables

1. Update the `.env` file with your Slack and AWS credentials:

```
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token

# AWS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=your-region  # e.g., us-east-1

# AWS Knowledge Base Configuration 
AWS_KNOWLEDGE_BASE_ID=your-knowledge-base-id
```

## Running the Bot

1. Install dependencies:
```
npm install
```

2. Start the bot:
```
npm start
```

## Populating the Knowledge Base

The project includes a utility script to help upload documents to your AWS knowledge base:

1. Ensure your `.env` file has the correct AWS credentials and knowledge base ID
2. Run the upload script:
```
npm run upload-doc ./path/to/document.txt
```

3. You can include optional metadata as a JSON string:
```
npm run upload-doc ./path/to/document.txt '{"category":"compute","service":"EC2"}'
```

This will upload the document content to your AWS knowledge base, making it available for the bot to use when answering questions.

## Using the Bot

### In Channels
Mention the bot followed by your question:
```
@your-bot-name What EC2 instance types are available?
```

### In Direct Messages
Simply send your question directly to the bot:
```
What is AWS Lambda?
```

## Customization

You can modify `index.js` to:
- Change how responses are formatted
- Add additional AWS services
- Implement rate limiting
- Add support for specific channels only

## Troubleshooting

If you encounter issues:
1. Check the console logs for error messages
2. Verify your AWS credentials and permissions
3. Ensure the knowledge base ID is correct
4. Check that all required Slack scopes are granted
