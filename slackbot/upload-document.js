#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
require('dotenv').config();

// Check for required arguments
if (process.argv.length < 3) {
  console.log('Usage: node upload-document.js <file-path> [metadata-json]');
  console.log('Example: node upload-document.js ./docs/ec2.txt \'{"category":"compute"}\'');
  process.exit(1);
}

/**
 * Upload a document to the AWS knowledge base using AWS SDK v2
 */
async function uploadDocument() {
  const filePath = process.argv[2];
  let metadata = {};
  
  // Optional metadata as JSON string
  if (process.argv[3]) {
    try {
      metadata = JSON.parse(process.argv[3]);
    } catch (error) {
      console.error('Error parsing metadata JSON:', error.message);
      process.exit(1);
    }
  }

  try {
    // Read the file content
    const fileContent = fs.readFileSync(filePath, 'utf8');
    const fileName = path.basename(filePath);
    
    // Import aws-sdk v2 (which we already have as a dependency)
    const AWS = require('aws-sdk');
    
    // Configure AWS SDK v2
    AWS.config.update({
      accessKeyId: process.env.AWS_ACCESS_KEY_ID,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      region: process.env.AWS_REGION
    });
    
    // Create a low-level client using AWS.Request
    const endpoint = `bedrock-agent-runtime.${process.env.AWS_REGION}.amazonaws.com`;
    const req = new AWS.HttpRequest(new AWS.Endpoint(endpoint), process.env.AWS_REGION);
    
    // Set up the request parameters
    req.method = 'POST';
    req.path = '/ingestDocument';
    req.headers['Content-Type'] = 'application/json';
    req.headers['X-Amz-Target'] = 'BedrockAgentRuntime.IngestDocument';
    
    // Add the payload
    const payload = {
      knowledgeBaseId: process.env.AWS_KNOWLEDGE_BASE_ID,
      documents: [
        {
          content: {
            text: fileContent
          },
          metadata: {
            ...metadata,
            source: fileName,
            uploadedAt: new Date().toISOString()
          }
        }
      ]
    };
    
    req.body = JSON.stringify(payload);

    console.log(`Uploading document: ${fileName}`);
    
    // Sign the request
    const signer = new AWS.Signers.V4(req, 'bedrock');
    signer.addAuthorization(AWS.config.credentials, new Date());
    
    // Send the request
    const response = await new Promise((resolve, reject) => {
      const send = new AWS.NodeHttpClient();
      send.handleRequest(req, null, function(httpResp) {
        let respBody = '';
        httpResp.on('data', function(chunk) {
          respBody += chunk;
        });
        httpResp.on('end', function() {
          if (httpResp.statusCode === 200) {
            resolve(JSON.parse(respBody));
          } else {
            reject(new Error(`HTTP Status: ${httpResp.statusCode}, Body: ${respBody}`));
          }
        });
      }, function(err) {
        reject(err);
      });
    });
    
    console.log('Document uploaded successfully!');
    console.log('Response:', JSON.stringify(response, null, 2));
    
    return response;
  } catch (error) {
    console.error('Error uploading document:', error.message);
    if (error.message?.includes('AccessDenied')) {
      console.error('Make sure your IAM user has sufficient permissions for Bedrock Knowledge Bases.');
    } else if (error.message?.includes('ResourceNotFound')) {
      console.error(`Knowledge base with ID ${process.env.AWS_KNOWLEDGE_BASE_ID} not found.`);
    }
    process.exit(1);
  }
}

uploadDocument();
