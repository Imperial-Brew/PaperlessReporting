# PaperlessReporting Security Testing Plan

This document outlines the comprehensive testing plan for verifying the security improvements made to the PaperlessReporting project. The tests are designed to ensure that sensitive credentials are properly protected and that the application handles authentication and errors securely.

## Prerequisites

Before running the tests, ensure you have:

1. Set up your environment variables in the `.env` file with valid credentials:
   - `WEBHOOK_SECRET`: Your webhook secret
   - `PAPERLESS_API_TOKEN`: Your Paperless Parts API token
   - `AWS_ACCESS_KEY_ID`: Your AWS access key
   - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
   - `S3_BUCKET_NAME`: Your S3 bucket name
   - `AWS_DEFAULT_REGION`: Your AWS region

2. Installed all required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. The webhook server should be running for some tests:
   ```
   python -m scripts.app
   ```

## Test Scripts

The following PowerShell scripts have been created to test different aspects of the application's security:

### 1. Webhook Authentication Test

**Script**: `tests\test_webhook_auth.ps1`

**Purpose**: Verifies that the webhook authentication mechanisms work correctly after security improvements.

**What it tests**:
- Header-based authentication using HMAC-SHA256 signature
- Token parameter authentication using the webhook secret
- Rejection of unauthorized requests

**How to run**:
```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting
.\tests\test_webhook_auth.ps1
```

**Expected results**:
- Header-based authentication should succeed
- Token parameter authentication should succeed
- Unauthorized requests should be rejected with a 401 status code

### 2. S3 Upload Test

**Script**: `tests\test_s3_upload.ps1`

**Purpose**: Verifies that the S3 upload functionality works correctly with the new secure configuration.

**What it tests**:
- Creation of a test CSV file
- Direct upload to S3 using the `upload_to_s3` function
- Proper handling of AWS credentials

**How to run**:
```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting
.\tests\test_s3_upload.ps1
```

**Expected results**:
- The test CSV file should be created successfully
- The upload to S3 should succeed
- The file should be visible in the S3 bucket under the `paperless/` prefix

### 3. API Integration Test

**Script**: `tests\test_api_integration.ps1`

**Purpose**: Verifies that the Paperless Parts API integration works correctly with the new API token.

**What it tests**:
- Basic API connection
- Quotes API functionality
- Orders API functionality
- Provides instructions for end-to-end webhook testing

**How to run**:
```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting
.\tests\test_api_integration.ps1
```

**Expected results**:
- API connection should succeed
- Quotes API request should return data
- Orders API request should return data

### 4. Log Security Test

**Script**: `tests\test_log_security.ps1`

**Purpose**: Verifies that sensitive credentials are properly redacted in logs.

**What it tests**:
- Webhook server credential logging
- S3 helpers credential logging
- Analysis of logs for credential exposure

**How to run**:
```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting
.\tests\test_log_security.ps1
```

**Expected results**:
- No actual or partial credentials should be found in logs
- Proper redaction markers (`[REDACTED]`) should be found in logs
- Example log lines should show redacted credentials

### 5. Error Handling Test

**Script**: `tests\test_error_handling.ps1`

**Purpose**: Verifies that the application handles errors securely without exposing sensitive information.

**What it tests**:
- S3 upload with invalid AWS credentials
- Webhook authentication with invalid secret
- Analysis of error output for credential exposure

**How to run**:
```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting
.\tests\test_error_handling.ps1
```

**Expected results**:
- S3 upload should fail with invalid credentials
- No actual credentials should be exposed in error output
- Webhook authentication should reject invalid signatures
- No webhook secrets should be exposed in error output

## Running All Tests

To run all tests in sequence, you can use the following PowerShell script:

```powershell
cd F:\Dustin Drab\CURSOR\PaperlessReporting

Write-Host "=== Running All Security Tests ===" -ForegroundColor Cyan

# Start the webhook server in the background (if needed)
# Start-Process python -ArgumentList "-m scripts.app" -NoNewWindow

# Run each test
Write-Host "`n1. Running Webhook Authentication Test..." -ForegroundColor Green
.\tests\test_webhook_auth.ps1

Write-Host "`n2. Running S3 Upload Test..." -ForegroundColor Green
.\tests\test_s3_upload.ps1

Write-Host "`n3. Running API Integration Test..." -ForegroundColor Green
.\tests\test_api_integration.ps1

Write-Host "`n4. Running Log Security Test..." -ForegroundColor Green
.\tests\test_log_security.ps1

Write-Host "`n5. Running Error Handling Test..." -ForegroundColor Green
.\tests\test_error_handling.ps1

Write-Host "`n=== All Security Tests Completed ===" -ForegroundColor Cyan
```

## Interpreting Test Results

Each test script provides clear output with success (✅) and failure (❌) indicators. Pay attention to:

1. **Authentication Tests**: Ensure all authentication methods work and unauthorized requests are rejected.
2. **S3 Upload Tests**: Verify that files are successfully uploaded to S3 and check the AWS Console.
3. **API Integration Tests**: Confirm that the API connection works and returns expected data.
4. **Log Security Tests**: Look for proper redaction of credentials in logs.
5. **Error Handling Tests**: Ensure errors are handled securely without exposing credentials.

## Security Recommendations

Based on the security assessment and testing, here are additional recommendations for further improving the security of the PaperlessReporting project:

1. **Regular Credential Rotation**:
   - Implement a schedule for rotating all credentials (API tokens, AWS keys, webhook secrets)
   - Document the rotation process and maintain a rotation log

2. **Enhanced Authentication**:
   - Consider implementing a more robust webhook authentication mechanism
   - Deprecate the token parameter method in favor of the more secure header-based method

3. **Dependency Management**:
   - Regularly update dependencies to address security vulnerabilities
   - Implement a dependency scanning tool in the CI/CD pipeline

4. **Monitoring and Alerting**:
   - Set up monitoring for suspicious activities
   - Implement alerting for authentication failures and other security events

5. **Security Documentation**:
   - Create a SECURITY.md file with instructions for reporting security vulnerabilities
   - Document security best practices for developers working on the project

6. **Secure Development Practices**:
   - Implement code reviews with a focus on security
   - Conduct regular security training for developers

## Conclusion

The security improvements made to the PaperlessReporting project have significantly enhanced its security posture. By removing hardcoded secrets, properly redacting sensitive information in logs, and ensuring secure error handling, the application is now better protected against potential security risks.

The test scripts provided in this plan allow for ongoing verification of these security improvements and can be used as part of a regular security testing routine.