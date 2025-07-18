const { App } = require('@slack/bolt');
const { BedrockAgentRuntimeClient, RetrieveCommand } = require('@aws-sdk/client-bedrock-agent-runtime');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');
require('dotenv').config();

// Initialize Slack Bolt app
const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN,
});

// Initialize AWS Bedrock clients
const bedrockAgentClient = new BedrockAgentRuntimeClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

// Initialize Bedrock Runtime client for LLM invocation
const bedrockRuntimeClient = new BedrockRuntimeClient({
  region: process.env.AWS_REGION,
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  },
});

// Default LLM model to use when knowledge base doesn't have an answer
const DEFAULT_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0";

/**
 * Query AWS Bedrock LLM
 * @param {string} question - The question to ask the LLM
 * @param {string} context - Optional context from knowledge base
 * @returns {Promise<string>} - The LLM's response
 */
async function queryLLM(question, context = '') {
  try {
    const modelId = process.env.AWS_LLM_MODEL_ID || DEFAULT_MODEL_ID;
    
    // Prepare the prompt based on whether we have context or not
    const prompt = context ? 
      `Human: I need information about AWS. Here's some context:\n${context}\n\nAnswer this question concisely:\n${question}\n\nAssistant:` : 
      `Human: Answer this AWS-related question concisely:\n${question}\n\nAssistant:`;
    
    // Prepare the request payload based on the model
    let payload;
    
    if (modelId.includes('anthropic')) {
      // Claude models
      payload = {
        anthropic_version: "bedrock-2023-05-31",
        max_tokens: 1000,
        messages: [{ role: "user", content: prompt }]
      };
    } else if (modelId.includes('amazon.titan')) {
      // Amazon Titan models
      payload = {
        inputText: prompt,
        textGenerationConfig: {
          maxTokenCount: 1000,
          stopSequences: [],
          temperature: 0.7,
          topP: 0.9
        }
      };
    } else {
      throw new Error(`Unsupported model: ${modelId}`);
    }
    
    // Invoke the model
    const command = new InvokeModelCommand({
      modelId: modelId,
      contentType: "application/json",
      accept: "application/json",
      body: JSON.stringify(payload)
    });
    
    const response = await bedrockRuntimeClient.send(command);
    
    // Parse the response body based on the model
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));
    
    let answer;
    if (modelId.includes('anthropic')) {
      answer = responseBody.content[0].text;
    } else if (modelId.includes('amazon.titan')) {
      answer = responseBody.results[0].outputText;
    } else {
      answer = "Response format not recognized";
    }
    
    return answer;
  } catch (error) {
    console.error('Error querying LLM:', error);
    return "Sorry, I encountered an error while generating a response.";
  }
}

/**
 * Query AWS Knowledge Base
 * @param {string} question - The question to query
 * @returns {Promise<{answer: string, foundInKB: boolean, rawResults: any}>}
 */
async function queryKnowledgeBase(question) {
  try {
    const params = {
      knowledgeBaseId: process.env.AWS_KNOWLEDGE_BASE_ID,
      retrievalQuery: { text: question }
    };
    
    const command = new RetrieveCommand(params);
    const response = await bedrockAgentClient.send(command);
    
    // Check if we got meaningful results
    if (response.retrievalResults && response.retrievalResults.length > 0) {
      // Combine all the results into a single context string
      const context = response.retrievalResults
        .map(result => result.content.text)
        .join('\n\n');
      
      return { 
        answer: await queryLLM(question, context),
        foundInKB: true,
        rawResults: response.retrievalResults
      };
    } else {
      return {
        answer: await queryLLM(question),
        foundInKB: false,
        rawResults: null
      };
    }
  } catch (error) {
    console.error('Error querying knowledge base:', error);
    
    // Fall back to LLM if the knowledge base query fails
    return {
      answer: await queryLLM(question),
      foundInKB: false,
      rawResults: null
    };
  }
}

// Process messages that mention the bot
app.event('app_mention', async ({ event, say }) => {
  try {
    // Extract the question from the message
    const question = event.text.replace(/<@[^>]+>/, '').trim();
    
    // Only respond if there's an actual question
    if (question) {
      // Let users know we're processing their request
      await say({
        text: `:thinking_face: Looking into: "${question}"`,
        thread_ts: event.ts
      });
      
      // Query the knowledge base and/or LLM
      const result = await queryKnowledgeBase(question);
      
      // Send the answer in the same thread
      await say({
        text: result.answer,
        thread_ts: event.ts
      });
    }
  } catch (error) {
    console.error('Error processing app_mention event:', error);
    await say({
      text: "Sorry, I encountered an error while processing your question.",
      thread_ts: event.ts
    });
  }
});

// Process direct messages and channel messages
app.message(async ({ message, say }) => {
  // Ignore bot messages (including our own)
  if (message.bot_id) return;
  
  try {
    const question = message.text.trim();
    
    // Skip empty messages
    if (!question) return;
    
    console.log(`Received message in ${message.channel_type === 'im' ? 'DM' : 'channel'}: "${question}"`);
    
    // Let users know we're processing their request
    await say({
      text: `:thinking_face: Looking into: "${question}"`,
      thread_ts: message.thread_ts || message.ts
    });
    
    // Query the knowledge base and/or LLM
    const result = await queryKnowledgeBase(question);
    
    // Send the response in the appropriate place
    await say({
      text: result.answer,
      thread_ts: message.thread_ts || message.ts
    });
    
    console.log(`Sent response for question: "${question}"`);
  } catch (error) {
    console.error('Error processing message:', error);
    await say({
      text: "Sorry, I encountered an error while processing your question.",
      thread_ts: message.thread_ts || message.ts
    });
  }
});

// Start the app
(async () => {
  await app.start(process.env.PORT || 3000);
  console.log('⚡️ Slack bot is running!');
})();
