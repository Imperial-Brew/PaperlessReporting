# Error Handling Test Script
# This script tests error handling with invalid credentials

Write-Host "=== Error Handling Testing ===" -ForegroundColor Cyan

# 1. Test S3 upload with invalid AWS credentials
Write-Host "`n1. Testing S3 upload with invalid AWS credentials..." -ForegroundColor Green

# Create a test CSV file
$testCsvPath = ".\error_test.csv"
"test1,test2`nvalue1,value2" | Out-File -FilePath $testCsvPath -Encoding utf8

# Save original AWS credentials
$originalAccessKey = $env:AWS_ACCESS_KEY_ID
$originalSecretKey = $env:AWS_SECRET_ACCESS_KEY

# Set invalid AWS credentials
$env:AWS_ACCESS_KEY_ID = "AKIAINVALIDKEYINVALIDKEY"
$env:AWS_SECRET_ACCESS_KEY = "InvalidSecretKeyInvalidSecretKeyInvalidSecretKey"

$pythonScript1 = @"
import os
import sys
import logging
from scripts.utils.logging_config import configure_logging
from scripts.utils.s3_helpers import upload_to_s3

# Configure logging
os.environ['LOG_LEVEL'] = 'DEBUG'
configure_logging()
logger = logging.getLogger('test_error_handling')

logger.info("=== Testing S3 upload with invalid credentials ===")

# Create a test file
test_file_path = "$testCsvPath"

try:
    # This should fail due to invalid credentials
    result = upload_to_s3(test_file_path)
    print(f"Upload result: {'Success' if result else 'Failed'}")
    if result:
        print("ERROR: Upload succeeded with invalid credentials!")
        sys.exit(1)
    else:
        print("Expected failure occurred with invalid credentials")
except Exception as e:
    print(f"Exception occurred: {str(e)}")

print("S3 error handling test completed.")
"@

$pythonScriptPath1 = ".\test_s3_error.py"
$pythonScript1 | Out-File -FilePath $pythonScriptPath1 -Encoding utf8

try {
    Write-Host "Running Python script to test S3 error handling..."
    $output = python $pythonScriptPath1
    Write-Host $output
    
    # Check if the output contains any actual AWS credentials
    $credentialPatterns = @('AKIA[0-9A-Z]{16}', '[A-Za-z0-9+/]{40}')
    $exposureFound = $false
    
    foreach ($pattern in $credentialPatterns) {
        if ($output -match $pattern) {
            $exposureFound = $true
            Write-Host "❌ Found potential credential exposure in output!" -ForegroundColor Red
            break
        }
    }
    
    if (-not $exposureFound) {
        Write-Host "✅ No credential exposure detected in error output" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error executing Python script!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

# Restore original AWS credentials
if ($originalAccessKey) {
    $env:AWS_ACCESS_KEY_ID = $originalAccessKey
} else {
    Remove-Item Env:\AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue
}

if ($originalSecretKey) {
    $env:AWS_SECRET_ACCESS_KEY = $originalSecretKey
} else {
    Remove-Item Env:\AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue
}

Write-Host "Restored original AWS credentials"

# 2. Test webhook authentication with invalid secret
Write-Host "`n2. Testing webhook authentication with invalid secret..." -ForegroundColor Green

# Save original webhook secret
$originalWebhookSecret = $env:WEBHOOK_SECRET

# Set invalid webhook secret
$env:WEBHOOK_SECRET = "invalid-webhook-secret"

$pythonScript2 = @"
import os
import sys
import logging
import json
import hmac
import hashlib
from scripts.utils.logging_config import configure_logging
from scripts.webhook_server import WebhookServer

# Configure logging
os.environ['LOG_LEVEL'] = 'DEBUG'
configure_logging()
logger = logging.getLogger('test_error_handling')

logger.info("=== Testing webhook authentication with invalid secret ===")

# Create a test payload
payload = {
    "type": "quote.status_changed",
    "data": {
        "quote_number": "TEST-001",
        "revision_number": "1",
        "status": "Sent"
    }
}
payload_bytes = json.dumps(payload).encode()

# Create a webhook server with the invalid secret
try:
    webhook_server = WebhookServer(webhook_secret="correct-secret")
    
    # Calculate signature with a different secret
    wrong_signature = hmac.new(
        "wrong-secret".encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    print(f"Using intentionally wrong signature: {wrong_signature}")
    
    # This should fail authentication
    print("Testing authentication with wrong signature (should fail)...")
    # Simulate authentication check
    try:
        # We can't directly call the webhook endpoint, so we'll simulate the authentication check
        # by creating a mock request object with the wrong signature
        class MockRequest:
            def __init__(self):
                self.headers = {"X-Webhook-Signature": wrong_signature}
                self.args = {}
                self.data = payload_bytes
        
        # This should raise an authentication error
        webhook_server._authenticate_webhook(MockRequest())
        print("ERROR: Authentication succeeded with wrong signature!")
        sys.exit(1)
    except Exception as e:
        print(f"Expected authentication failure occurred: {str(e)}")
        print("✅ Webhook authentication correctly rejected invalid signature")
    
except Exception as e:
    print(f"Unexpected error: {str(e)}")

print("Webhook error handling test completed.")
"@

$pythonScriptPath2 = ".\test_webhook_error.py"
$pythonScript2 | Out-File -FilePath $pythonScriptPath2 -Encoding utf8

try {
    Write-Host "Running Python script to test webhook error handling..."
    $output = python $pythonScriptPath2
    Write-Host $output
    
    # Check if the output contains any actual webhook secrets
    if ($output -match "supersecret") {
        Write-Host "❌ Found hardcoded webhook secret in output!" -ForegroundColor Red
    } else {
        Write-Host "✅ No webhook secret exposure detected in error output" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Error executing Python script!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

# Restore original webhook secret
if ($originalWebhookSecret) {
    $env:WEBHOOK_SECRET = $originalWebhookSecret
} else {
    Remove-Item Env:\WEBHOOK_SECRET -ErrorAction SilentlyContinue
}

Write-Host "Restored original webhook secret"

# 3. Clean up
Write-Host "`n3. Cleaning up..." -ForegroundColor Green

try {
    Remove-Item -Path $testCsvPath -ErrorAction SilentlyContinue
    Remove-Item -Path $pythonScriptPath1 -ErrorAction SilentlyContinue
    Remove-Item -Path $pythonScriptPath2 -ErrorAction SilentlyContinue
    Write-Host "✅ Temporary files cleaned up successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Could not clean up some temporary files." -ForegroundColor Yellow
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`n=== Error Handling Testing Complete ===" -ForegroundColor Cyan