#!/usr/bin/env python3
"""Test different ways to call Amazon Q CLI."""

import subprocess
import tempfile
import os

def test_direct_string():
    """Test passing prompt as direct string."""
    print("Test 1: Direct string input")
    prompt = "How do I list files in Linux?"
    
    cmd = ['q', 'chat', prompt]
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Output: {result.stdout}")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed: {e}")
    print("-" * 80)

def test_multiline_string():
    """Test passing multiline prompt as string."""
    print("\nTest 2: Multiline string input")
    prompt = """Analyze this error:
Error: Connection timeout
Service: api-gateway
Time: 2024-01-01 10:00:00

What could be the root cause?"""
    
    # For multiline, we might need to escape or use stdin
    cmd = ['q', 'chat', prompt]
    print(f"Command: q chat [multiline prompt]")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed: {e}")
    print("-" * 80)

def test_with_file():
    """Test passing prompt from file."""
    print("\nTest 3: File input")
    
    # Create a temp file with the prompt
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("""You are investigating the following question: Why is my deployment experiencing high latency?

Investigation History:
- 2024-01-01 10:00:00: Started investigation
- 2024-01-01 10:01:00: Checked service metrics

Current Findings:
- Error rate: 5%
- P99 latency: 2000ms
- CPU usage: 85%

Based on the above context, continue the investigation.
If you have enough information to answer the question, respond with 'INVESTIGATION_COMPLETE: <answer>'.
Otherwise, describe the next investigation steps needed.""")
        prompt_file = f.name
    
    try:
        # Try different approaches
        # Approach 1: Using file redirection
        print("Approach 1: Using shell redirection")
        cmd = f"q chat < {prompt_file}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Output: {result.stdout[:200]}...")
        
        # Approach 2: Reading file and passing as argument
        print("\nApproach 2: Reading file content")
        with open(prompt_file, 'r') as f:
            content = f.read()
        cmd = ['q', 'chat', content]
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"Output: {result.stdout[:200]}...")
        
    except Exception as e:
        print(f"Failed: {e}")
    finally:
        os.unlink(prompt_file)
    print("-" * 80)

def test_with_stdin():
    """Test passing prompt via stdin."""
    print("\nTest 4: STDIN input")
    
    prompt = """Investigate high latency issue.
Current metrics: P99=2000ms, Error=5%
What's the root cause?"""
    
    try:
        # Pass via stdin
        result = subprocess.run(
            ['q', 'chat'],
            input=prompt,
            capture_output=True,
            text=True
        )
        print(f"Output: {result.stdout[:200]}...")
        if result.stderr:
            print(f"Error: {result.stderr}")
    except Exception as e:
        print(f"Failed: {e}")
    print("-" * 80)

if __name__ == "__main__":
    print("Testing Amazon Q CLI input methods...\n")
    
    # Check if q command exists
    try:
        subprocess.run(['q', '--version'], capture_output=True, check=True)
        print("✓ Amazon Q CLI is installed\n")
    except:
        print("❌ Amazon Q CLI not found. Install with: brew install amazon-q")
        print("   Or download from: https://aws.amazon.com/q/developer/")
        exit(1)
    
    # Run tests
    test_direct_string()
    test_multiline_string()
    test_with_file()
    test_with_stdin()
    
    print("\nTests completed!")