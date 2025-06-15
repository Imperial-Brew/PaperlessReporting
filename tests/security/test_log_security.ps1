# Log Security Test Script
# This script tests that sensitive credentials are properly redacted in logs

Write-Host "=== Log Security Testing ===" -ForegroundColor Cyan

# 1. Create a temporary log file with DEBUG level
Write-Host "`n1. Setting up DEBUG logging..." -ForegroundColor Green

$tempLogFile = ".\temp_debug.log"
$originalLogLevel = $env:LOG_LEVEL

# Set DEBUG log level for this test
$env:LOG_LEVEL = "DEBUG"
Write-Host "Temporarily set LOG_LEVEL to DEBUG"

# 2. Test webhook_server.py logging
Write-Host "`n2. Testing webhook_server.py logging..." -ForegroundColor Green

$pythonScript1 = @"
import os
import logging
from scripts.utils.logging_config import configure_logging
from scripts.webhook_server import WEBHOOK_SECRET, API_TOKEN

# Configure logging to file
os.environ['LOG_LEVEL'] = 'DEBUG'
configure_logging(log_file='$tempLogFile')
logger = logging.getLogger('test_log_security')

logger.info("=== Testing webhook_server.py credential logging ===")
logger.info(f"Webhook Secret should be redacted: {WEBHOOK_SECRET}")
logger.info(f"API Token should be redacted: {API_TOKEN}")
logger.info("=== End of webhook_server.py test ===")

print("Webhook server logging test completed. Check the log file for results.")
"@

$pythonScriptPath1 = ".\test_webhook_logging.py"
$pythonScript1 | Out-File -FilePath $pythonScriptPath1 -Encoding utf8

try {
    Write-Host "Running Python script to test webhook_server.py logging..."
    $output = python $pythonScriptPath1
    Write-Host $output
} catch {
    Write-Host "❌ Error executing Python script!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

# 3. Test s3_helpers.py logging
Write-Host "`n3. Testing s3_helpers.py logging..." -ForegroundColor Green

$pythonScript2 = @"
import os
import logging
from scripts.utils.logging_config import configure_logging

# Configure logging to file
os.environ['LOG_LEVEL'] = 'DEBUG'
configure_logging(log_file='$tempLogFile')
logger = logging.getLogger('test_log_security')

logger.info("=== Testing s3_helpers.py credential logging ===")

# Import s3_helpers after configuring logging to capture its initialization logs
from scripts.utils.s3_helpers import _aws_access_key, _aws_secret_key, _bucket, _region

# Force some additional logging
logger.info(f"Manual test - AWS access key should be redacted: {_aws_access_key}")
logger.info(f"Manual test - AWS secret key should be redacted: {_aws_secret_key}")
logger.info(f"S3 bucket (not sensitive): {_bucket}")
logger.info(f"AWS region (not sensitive): {_region}")
logger.info("=== End of s3_helpers.py test ===")

print("S3 helpers logging test completed. Check the log file for results.")
"@

$pythonScriptPath2 = ".\test_s3_logging.py"
$pythonScript2 | Out-File -FilePath $pythonScriptPath2 -Encoding utf8

try {
    Write-Host "Running Python script to test s3_helpers.py logging..."
    $output = python $pythonScriptPath2
    Write-Host $output
} catch {
    Write-Host "❌ Error executing Python script!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

# 4. Check the log file for credential exposure
Write-Host "`n4. Analyzing log file for credential exposure..." -ForegroundColor Green

if (Test-Path $tempLogFile) {
    $logContent = Get-Content $tempLogFile -Raw
    
    # Define patterns to search for
    $patterns = @(
        # Look for actual credentials (this would be bad)
        'AKIA[0-9A-Z]{16}',
        '[0-9a-f]{40}',
        # Look for partial credentials (this would be bad)
        'AKIA...',
        'bb21...',
        # Look for proper redaction (this is good)
        '\[REDACTED\]'
    )
    
    $exposureFound = $false
    $redactionFound = $false
    
    foreach ($pattern in $patterns) {
        $matches = Select-String -InputObject $logContent -Pattern $pattern -AllMatches
        
        if ($matches) {
            if ($pattern -eq '\[REDACTED\]') {
                $redactionFound = $true
                Write-Host "✅ Found proper redaction '[REDACTED]' in logs ($($matches.Matches.Count) occurrences)" -ForegroundColor Green
            } else {
                $exposureFound = $true
                Write-Host "❌ Found potential credential exposure matching pattern '$pattern'" -ForegroundColor Red
                Write-Host "   This indicates that credentials might not be properly redacted!" -ForegroundColor Red
            }
        }
    }
    
    if (-not $exposureFound -and $redactionFound) {
        Write-Host "✅ No credential exposure detected in logs!" -ForegroundColor Green
        Write-Host "   All sensitive information appears to be properly redacted." -ForegroundColor Green
    } elseif (-not $exposureFound -and -not $redactionFound) {
        Write-Host "⚠️ No credential patterns found in logs, but also no redaction markers." -ForegroundColor Yellow
        Write-Host "   This might indicate that the logging code wasn't executed." -ForegroundColor Yellow
    }
    
    # Display log excerpts with [REDACTED]
    $redactedLines = Select-String -Path $tempLogFile -Pattern "\[REDACTED\]" | Select-Object -ExpandProperty Line
    if ($redactedLines) {
        Write-Host "`nExample log lines with redacted credentials:" -ForegroundColor Cyan
        foreach ($line in $redactedLines) {
            Write-Host "  $line"
        }
    }
} else {
    Write-Host "❌ Log file not found at $tempLogFile" -ForegroundColor Red
}

# 5. Clean up
Write-Host "`n5. Cleaning up..." -ForegroundColor Green

# Restore original log level
if ($originalLogLevel) {
    $env:LOG_LEVEL = $originalLogLevel
    Write-Host "Restored LOG_LEVEL to $originalLogLevel"
} else {
    Remove-Item Env:\LOG_LEVEL -ErrorAction SilentlyContinue
    Write-Host "Removed temporary LOG_LEVEL environment variable"
}

# Remove temporary files
try {
    Remove-Item -Path $tempLogFile -ErrorAction SilentlyContinue
    Remove-Item -Path $pythonScriptPath1 -ErrorAction SilentlyContinue
    Remove-Item -Path $pythonScriptPath2 -ErrorAction SilentlyContinue
    Write-Host "✅ Temporary files cleaned up successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Could not clean up some temporary files." -ForegroundColor Yellow
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`n=== Log Security Testing Complete ===" -ForegroundColor Cyan