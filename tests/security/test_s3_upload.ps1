# S3 Upload Test Script
# This script tests the S3 upload functionality after security improvements

Write-Host "=== S3 Upload Testing ===" -ForegroundColor Cyan

# 1. Create a test CSV file
$testCsvPath = ".\test_upload.csv"
$testCsvContent = @"
quote_number,revision_number,status,created,due_date
TEST-001,1,Sent,2023-01-01,2023-01-15
TEST-002,1,Draft,2023-01-02,2023-01-16
"@

Write-Host "`n1. Creating test CSV file at $testCsvPath..." -ForegroundColor Green
try {
    $testCsvContent | Out-File -FilePath $testCsvPath -Encoding utf8
    Write-Host "✅ Test CSV file created successfully!" -ForegroundColor Green
    Write-Host "File content:"
    Get-Content $testCsvPath | ForEach-Object { Write-Host "  $_" }
} catch {
    Write-Host "❌ Failed to create test CSV file!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
    exit 1
}

# 2. Test direct upload to S3 using Python script
Write-Host "`n2. Testing S3 upload using Python script..." -ForegroundColor Green

$pythonScript = @"
from scripts.utils.s3_helpers import upload_to_s3
import os
import sys

# Get the absolute path to the test CSV file
test_csv_path = os.path.abspath("$testCsvPath")
print(f"Uploading file: {test_csv_path}")

# Check if file exists
if not os.path.exists(test_csv_path):
    print(f"Error: File not found at {test_csv_path}")
    sys.exit(1)

# Attempt to upload
result = upload_to_s3(test_csv_path)
print(f"Upload result: {'Success' if result else 'Failed'}")
sys.exit(0 if result else 1)
"@

$pythonScriptPath = ".\test_s3_upload.py"
$pythonScript | Out-File -FilePath $pythonScriptPath -Encoding utf8

try {
    Write-Host "Running Python script to test S3 upload..."
    $output = python $pythonScriptPath
    Write-Host $output
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ S3 upload test successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ S3 upload test failed!" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Error executing Python script!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)"
}

# 3. Verification instructions
Write-Host "`n3. Verification Steps:" -ForegroundColor Green
Write-Host "   To verify the upload was successful, please check the AWS S3 Console:" -ForegroundColor Yellow
Write-Host "   1. Log into AWS Console"
Write-Host "   2. Navigate to S3 service"
Write-Host "   3. Open your bucket (check .env file for bucket name)"
Write-Host "   4. Look for the file 'paperless/test_upload.csv'"
Write-Host "   5. Verify the file content matches the test data"

# Clean up
Write-Host "`nCleaning up test files..." -ForegroundColor Green
try {
    Remove-Item -Path $testCsvPath -ErrorAction SilentlyContinue
    Remove-Item -Path $pythonScriptPath -ErrorAction SilentlyContinue
    Write-Host "✅ Test files cleaned up successfully!" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Warning: Could not clean up some test files." -ForegroundColor Yellow
    Write-Host "Error: $($_.Exception.Message)"
}

Write-Host "`n=== S3 Upload Testing Complete ===" -ForegroundColor Cyan