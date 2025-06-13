# Security Documentation

This document provides detailed information about security practices for the PaperlessReporting project.

## Credential Management

### API Keys and Tokens

The PaperlessReporting project uses the Paperless Parts API, which requires an API token for authentication. This token should be treated as a sensitive credential:

- Store the API token in the `.env` file for local development
- In production environments, set the token as an environment variable
- Rotate the API token regularly (recommended every 90 days)
- Use the principle of least privilege when creating API tokens

Example of proper API token usage:

```python
# Good practice - load from environment variable
import os
from dotenv import load_dotenv

load_dotenv()
api_token = os.getenv("PAPERLESS_API_TOKEN")

# Bad practice - hardcoded token
api_token = "bb2166a05a6aba9341734580af5b901677daa7c2"  # NEVER DO THIS
```

### AWS Credentials

The project uses AWS S3 for storing data. AWS credentials should be handled with care:

- Store AWS credentials in the `.env` file for local development
- In production, use IAM roles instead of access keys when possible
- If access keys are necessary, rotate them regularly
- Create IAM users with minimal permissions required for the application

Required AWS environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `AWS_DEFAULT_REGION`

### Webhook Secrets

The webhook server uses a secret to authenticate incoming webhook requests:

- Store the webhook secret in the `.env` file
- Use a strong, randomly generated secret
- Rotate the webhook secret regularly
- Verify webhook signatures for all incoming requests

## Secure Development Practices

### Code Reviews

All code changes should be reviewed for security issues before merging:

- Check for hardcoded credentials
- Verify proper input validation
- Ensure error handling doesn't expose sensitive information
- Confirm that authentication and authorization are properly implemented

### Dependency Management

Keep dependencies up to date to avoid security vulnerabilities:

- Regularly update dependencies with `pip install --upgrade -r requirements.txt`
- Use tools like `pip-audit` to check for vulnerable dependencies
- Consider using a dependency scanning tool in your CI/CD pipeline

### Secure Coding Guidelines

Follow these guidelines when writing code:

- Validate all input data, especially from external sources
- Use parameterized queries for database operations
- Implement proper error handling that doesn't expose sensitive information
- Follow the principle of least privilege
- Use secure defaults for all configurations

## Pre-commit Hooks

The project uses pre-commit hooks to prevent accidentally committing sensitive information.

### Setting Up Pre-commit

1. Install pre-commit:
   ```bash
   pip install pre-commit
   ```

2. Install the git hooks:
   ```bash
   pre-commit install
   ```

3. Create a secrets baseline (first-time setup):
   ```bash
   detect-secrets scan > .secrets.baseline
   ```

4. Run pre-commit manually:
   ```bash
   pre-commit run --all-files
   ```

### Available Hooks

The following hooks are configured in `.pre-commit-config.yaml`:

- **detect-secrets**: Scans for potential secrets in code
- **no-commit-to-branch**: Prevents direct commits to main/master
- **check-added-large-files**: Prevents committing large files
- **check-merge-conflict**: Checks for merge conflict strings
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML files
- **flake8**: Checks Python code style
- **isort**: Sorts Python imports
- **Custom hook**: Checks for .env files

### Handling False Positives

If detect-secrets flags something that is not actually a secret:

1. Update the baseline:
   ```bash
   detect-secrets scan --baseline .secrets.baseline
   ```

2. Audit the baseline to mark false positives:
   ```bash
   detect-secrets audit .secrets.baseline
   ```

## Environment File Security

The `.env` file contains sensitive information and should be handled carefully:

### Creating a Secure .env File

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Fill in your credentials with strong, unique values
3. Ensure the file has restricted permissions:
   ```bash
   chmod 600 .env  # On Unix-like systems
   ```

### Protecting .env Files

- Never commit `.env` files to version control
- The `.gitignore` file is configured to exclude `.env` files
- The pre-commit hooks include a check for `.env` files
- Each developer should create their own `.env` file
- Never share `.env` files via email, chat, or other insecure channels

## S3 Security

The project uses AWS S3 for storing data. Follow these best practices for S3 security:

### Bucket Policies

- Configure bucket policies to restrict access to authorized users only
- Use the principle of least privilege when granting permissions
- Consider using VPC endpoints for S3 access

Example bucket policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:role/PaperlessReportingRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

### Encryption

- Enable server-side encryption for S3 buckets
- Consider using AWS KMS for managing encryption keys
- Use HTTPS for all S3 API calls

### Access Logging

- Enable access logging for S3 buckets to track usage
- Regularly review access logs for unauthorized access attempts
- Consider setting up alerts for suspicious activity

## Incident Response

In case of a security incident:

1. Immediately rotate all compromised credentials
2. Assess the scope of the incident
3. Review access logs to determine the extent of the breach
4. Notify affected parties if required by law or contracts
5. Implement measures to prevent similar incidents in the future

## Security Checklist

Use this checklist to ensure your development environment is secure:

- [ ] `.env` file is created from `.env.example` and contains your credentials
- [ ] `.env` file is not committed to version control
- [ ] Pre-commit hooks are installed and running
- [ ] Dependencies are up to date
- [ ] Code has been reviewed for security issues
- [ ] S3 bucket has appropriate access controls
- [ ] Credentials are rotated regularly
- [ ] Access logging is enabled for S3 buckets
- [ ] Error handling doesn't expose sensitive information