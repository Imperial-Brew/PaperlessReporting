# Run All Security Tests Script
# This script runs all the security tests in sequence

Write-Host "=== Running All Security Tests ===" -ForegroundColor Cyan
Write-Host "This script will run all security tests to verify the improvements made to the PaperlessReporting project."

# Check if webhook server is running
$webhookServerRunning = $false
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get -ErrorAction Stop
    if ($response -eq "OK") {
        $webhookServerRunning = $true
        Write-Host "`nWebhook server is already running." -ForegroundColor Green
    }
} catch {
    Write-Host "`nWebhook server is not running." -ForegroundColor Yellow
}

# Prompt to start webhook server if not running
if (-not $webhookServerRunning) {
    $startServer = Read-Host "Do you want to start the webhook server for testing? (y/n)"
    if ($startServer -eq "y") {
        Write-Host "Starting webhook server in a new window..." -ForegroundColor Green
        Start-Process python -ArgumentList "-m scripts.app" -NoNewWindow

        # Wait for server to start
        Write-Host "Waiting for server to start..."
        Start-Sleep -Seconds 5

        # Check if server started successfully
        try {
            $response = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get -ErrorAction Stop
            if ($response -eq "OK") {
                Write-Host "Webhook server started successfully!" -ForegroundColor Green
            }
        } catch {
            Write-Host "Warning: Could not confirm webhook server is running. Some tests may fail." -ForegroundColor Yellow
        }
    } else {
        Write-Host "Continuing without webhook server. Some tests may fail." -ForegroundColor Yellow
    }
}

# Check for required environment variables
$requiredVars = @(
    "WEBHOOK_SECRET",
    "PAPERLESS_API_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "S3_BUCKET_NAME"
)

$missingVars = @()
foreach ($var in $requiredVars) {
    if (-not (Get-Item "env:$var" -ErrorAction SilentlyContinue)) {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "`nWarning: The following environment variables are not set:" -ForegroundColor Yellow
    foreach ($var in $missingVars) {
        Write-Host "  - $var" -ForegroundColor Yellow
    }
    Write-Host "Some tests may fail without these variables." -ForegroundColor Yellow

    $continue = Read-Host "Do you want to continue anyway? (y/n)"
    if ($continue -ne "y") {
        Write-Host "Exiting test suite." -ForegroundColor Red
        exit
    }
}

# Create a results directory for test outputs
$resultsDir = ".\test_results"
if (-not (Test-Path $resultsDir)) {
    New-Item -Path $resultsDir -ItemType Directory | Out-Null
    Write-Host "Created test results directory: $resultsDir" -ForegroundColor Green
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$resultsDir\security_tests_$timestamp.log"

# Function to run a test and log results
function Run-Test {
    param (
        [string]$TestName,
        [string]$ScriptPath
    )

    Write-Host "`n=== Running $TestName ===" -ForegroundColor Green

    # Log test start
    "=== $TestName ($(Get-Date)) ===" | Out-File -FilePath $logFile -Append

    # Run the test and capture output
    try {
        $output = & $ScriptPath
        $output | Out-File -FilePath $logFile -Append

        # Display output to console
        $output

        # Check for success/failure indicators in output
        $successCount = ($output | Select-String -Pattern "✅" -AllMatches).Matches.Count
        $failureCount = ($output | Select-String -Pattern "❌" -AllMatches).Matches.Count
        $warningCount = ($output | Select-String -Pattern "⚠️" -AllMatches).Matches.Count

        Write-Host "Results: $successCount successes, $failureCount failures, $warningCount warnings" -ForegroundColor Cyan

        # Log summary
        "Results: $successCount successes, $failureCount failures, $warningCount warnings`n" | Out-File -FilePath $logFile -Append

        return @{
            Success = $successCount
            Failure = $failureCount
            Warning = $warningCount
        }
    } catch {
        Write-Host "Error running test: $_" -ForegroundColor Red
        "Error running test: $_" | Out-File -FilePath $logFile -Append
        return @{
            Success = 0
            Failure = 1
            Warning = 0
        }
    }
}

# Run each test and collect results
$testResults = @{}

Write-Host "`nRunning tests and logging results to: $logFile" -ForegroundColor Cyan

# 1. Webhook Authentication Test
$testResults["Webhook Authentication"] = Run-Test -TestName "Webhook Authentication Test" -ScriptPath ".\tests\security\test_webhook_auth.ps1"

# 2. S3 Upload Test
$testResults["S3 Upload"] = Run-Test -TestName "S3 Upload Test" -ScriptPath ".\tests\security\test_s3_upload.ps1"

# 3. API Integration Test
$testResults["API Integration"] = Run-Test -TestName "API Integration Test" -ScriptPath ".\tests\security\test_api_integration.ps1"

# 4. Log Security Test
$testResults["Log Security"] = Run-Test -TestName "Log Security Test" -ScriptPath ".\tests\security\test_log_security.ps1"

# 5. Error Handling Test
$testResults["Error Handling"] = Run-Test -TestName "Error Handling Test" -ScriptPath ".\tests\security\test_error_handling.ps1"

# Generate summary report
Write-Host "`n=== Security Testing Summary ===" -ForegroundColor Cyan
"=== Security Testing Summary ($(Get-Date)) ===" | Out-File -FilePath "$resultsDir\summary_$timestamp.txt"

$totalSuccess = 0
$totalFailure = 0
$totalWarning = 0

foreach ($test in $testResults.Keys) {
    $result = $testResults[$test]
    $totalSuccess += $result.Success
    $totalFailure += $result.Failure
    $totalWarning += $result.Warning

    $status = if ($result.Failure -gt 0) { "⚠️ Issues Found" } else { "✅ Passed" }

    Write-Host "$test: $status ($($result.Success) successes, $($result.Failure) failures, $($result.Warning) warnings)" -ForegroundColor $(if ($result.Failure -gt 0) { "Yellow" } else { "Green" })
    "$test: $status ($($result.Success) successes, $($result.Failure) failures, $($result.Warning) warnings)" | Out-File -FilePath "$resultsDir\summary_$timestamp.txt" -Append
}

# Overall status
$overallStatus = if ($totalFailure -gt 0) { "⚠️ Issues Found" } else { "✅ All Tests Passed" }

Write-Host "`nOverall Status: $overallStatus" -ForegroundColor $(if ($totalFailure -gt 0) { "Yellow" } else { "Green" })
Write-Host "Total: $totalSuccess successes, $totalFailure failures, $totalWarning warnings" -ForegroundColor Cyan

"Overall Status: $overallStatus" | Out-File -FilePath "$resultsDir\summary_$timestamp.txt" -Append
"Total: $totalSuccess successes, $totalFailure failures, $totalWarning warnings" | Out-File -FilePath "$resultsDir\summary_$timestamp.txt" -Append

# Next steps
Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Review the detailed test logs in: $logFile"
Write-Host "2. Check the summary report in: $resultsDir\summary_$timestamp.txt"
Write-Host "3. Address any issues found during testing"
Write-Host "4. Refer to docs\TEST_PLAN.md for security recommendations"

Write-Host "`n=== All Security Tests Completed ===" -ForegroundColor Cyan
