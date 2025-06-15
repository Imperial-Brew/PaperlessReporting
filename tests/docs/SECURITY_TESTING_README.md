# Security Testing for PaperlessReporting

## Overview

This directory contains a comprehensive set of security tests designed to verify the security improvements made to the PaperlessReporting project. These tests focus on ensuring that sensitive credentials are properly protected, authentication mechanisms work correctly, and error handling is secure.

## Security Improvements Verified

The test suite verifies the following security improvements:

1. **Removal of Hardcoded Secrets**
   - Eliminated the hardcoded webhook secret fallback in webhook_server.py
   - Ensured all credentials are properly sourced from environment variables or configuration files

2. **Secure Credential Logging**
   - Replaced partial credential logging with "[REDACTED]" in webhook_server.py
   - Replaced partial AWS key logging with "[REDACTED]" in s3_helpers.py
   - Ensured error handling code doesn't expose credentials

3. **Secure Authentication**
   - Verified that webhook authentication works correctly with both methods
   - Ensured unauthorized requests are properly rejected

4. **Secure Error Handling**
   - Verified that error messages don't expose sensitive information
   - Ensured the application fails securely when credentials are invalid

## Test Suite Components

The test suite consists of the following components:

1. **Individual Test Scripts**
   - `test_webhook_auth.ps1`: Tests webhook authentication mechanisms
   - `test_s3_upload.ps1`: Tests S3 upload functionality
   - `test_api_integration.ps1`: Tests Paperless Parts API integration
   - `test_log_security.ps1`: Tests credential redaction in logs
   - `test_error_handling.ps1`: Tests secure error handling

2. **Test Runner**
   - `run_all_tests.ps1`: Runs all tests in sequence and generates a summary report

3. **Documentation**
   - `TEST_PLAN.md`: Comprehensive testing plan with details on each test
   - `SECURITY_TESTING_README.md`: This file, providing an overview of the security testing

## How to Use the Test Suite

### Prerequisites

Before running the tests, ensure you have:

1. Set up your environment variables in the `.env` file with valid credentials
2. Installed all required dependencies with `pip install -r requirements.txt`
3. The webhook server should be running for some tests (the test runner can start it for you)

### Running the Tests

You can run individual tests or the entire test suite:

#### Running Individual Tests

Each test script can be run independently:

```powershell
# Run from the project root directory
.\tests\test_webhook_auth.ps1
.\tests\test_s3_upload.ps1
.\tests\test_api_integration.ps1
.\tests\test_log_security.ps1
.\tests\test_error_handling.ps1
```

#### Running the Complete Test Suite

To run all tests and generate a comprehensive report:

```powershell
# Run from the project root directory
.\tests\run_all_tests.ps1
```

The test runner will:
1. Check if the webhook server is running and offer to start it if needed
2. Verify that required environment variables are set
3. Create a results directory for test outputs
4. Run each test and collect results
5. Generate a summary report with success/failure metrics

### Test Results

The test runner generates two types of output:

1. **Detailed Log File**: Contains the complete output from all tests
   - Located in `test_results\security_tests_[timestamp].log`

2. **Summary Report**: Provides an overview of test results
   - Located in `test_results\summary_[timestamp].txt`
   - Shows success/failure counts for each test
   - Indicates overall test suite status

## Regular Security Testing

It's recommended to run these security tests:

1. After making any changes to authentication or credential handling code
2. After updating dependencies
3. Before deploying to production
4. On a regular schedule (e.g., monthly) as part of security maintenance

## Extending the Test Suite

To add new security tests:

1. Create a new PowerShell script in the `tests` directory
2. Follow the pattern of existing tests, using clear success/failure indicators (✅/❌)
3. Update the `run_all_tests.ps1` script to include your new test
4. Update the `TEST_PLAN.md` document with details about your new test

## Security Best Practices

Remember to follow these security best practices:

1. Never commit credentials to the repository
2. Regularly rotate all credentials
3. Use strong, unique secrets for authentication
4. Keep dependencies updated to address security vulnerabilities
5. Implement proper logging that doesn't expose sensitive information
6. Handle errors securely without revealing implementation details

## Conclusion

The security testing suite provides a comprehensive way to verify that the PaperlessReporting project properly protects sensitive information and implements secure authentication and error handling. By regularly running these tests, you can ensure that security improvements are maintained and that new security issues are quickly identified and addressed.