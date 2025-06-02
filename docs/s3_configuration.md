# S3 Configuration Guide

## Overview

This document provides comprehensive information about AWS S3 configuration for the PaperlessReporting project, including setup instructions, troubleshooting, and best practices for Python imports.

## AWS S3 Setup

### Creating an S3 Bucket and IAM User

1. **Create an S3 Bucket**:
   - Log in to the AWS Management Console
   - Navigate to S3
   - Create a new bucket named "athena-paperless-csvs"
   - Configure the bucket settings as needed

2. **Create an IAM User with S3 Access**:
   - Navigate to IAM in the AWS Console
   - Create a new user with programmatic access
   - Attach the `AmazonS3FullAccess` policy (or a more restricted policy that allows access to the specific bucket)
   - Save the Access Key ID and Secret Access Key

### Configuration in the Application

To properly configure AWS S3 for the webhook server, you need to:

1. **Set Correct Environment Variables on Render**:
   - Make sure the following environment variables are set in the Render dashboard:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
     - `S3_BUCKET_NAME`: "athena-paperless-csvs"
     - `AWS_DEFAULT_REGION`: "us-west-2" (or your preferred region)

2. **Verify AWS Credentials**:
   - Ensure the AWS credentials have permission to upload to the S3 bucket
   - Check that the access key and secret key are correct and active in AWS IAM

3. **Test the Configuration**:
   - Run the test script to verify your S3 configuration:
     ```
     python scripts/test_s3_config.py
     ```
   - This script will:
     - Get the S3 configuration from environment variables or config.json
     - Create a test file
     - Attempt to upload the test file to S3
     - Report whether the upload was successful
     - Clean up the test file
   - The script will provide detailed logs about which credentials and bucket are being used, making it easier to diagnose any issues

## Common Issues and Troubleshooting

### Invalid AWS Credentials

If you encounter this error:
```
An error occurred (InvalidAccessKeyId) when calling the PutObject operation: The AWS Access Key Id you provided does not exist in our records.
```

This indicates that the AWS Access Key ID being used was not valid or did not have the necessary permissions to upload to the S3 bucket.

### Import Errors in Test Scripts

The `test_s3_config.py` script may encounter import errors when run with pytest:

```
ModuleNotFoundError: No module named 'utils'
```

This error occurs because of import path issues when running the script from different directories.

### Solutions for Import Issues

There are several approaches to fix import issues:

1. **Use Absolute Imports**:
   - Change `from utils.s3_helpers import upload_to_s3` to `from scripts.utils.s3_helpers import upload_to_s3`
   - Change `from utils.config_loader import get` to `from scripts.utils.config_loader import get`

2. **Use Dynamic Path Resolution**:
   ```python
   import sys
   from pathlib import Path
   
   # Add the parent directory to sys.path to allow imports from scripts.utils
   parent_dir = str(Path(__file__).parent.parent)
   if parent_dir not in sys.path:
       sys.path.append(parent_dir)
   
   from scripts.utils.s3_helpers import upload_to_s3
   from scripts.utils.config_loader import get
   ```

## Best Practices for Python Imports in Projects

When writing Python scripts that need to be run from different directories or with different tools like pytest, consider these best practices:

1. **Use Dynamic Path Resolution**: Add code to dynamically adjust `sys.path` based on the script's location.

2. **Create Proper Package Structure**: Ensure all directories that contain Python modules have `__init__.py` files to mark them as packages.

3. **Consider Using setuptools**: For larger projects, using setuptools and installing the package in development mode (`pip install -e .`) can solve many import issues.

4. **Be Consistent**: Follow the same import pattern throughout the project.

5. **Test from Different Contexts**: Make sure your scripts work when run from different directories and with different tools to catch import issues early.

## General Troubleshooting

If you continue to experience issues:

1. Check the logs for detailed error messages
2. Verify that the environment variables are set correctly in Render
3. Make sure the S3 bucket exists and is accessible
4. Ensure the IAM user has the necessary permissions
5. Try running the test script locally with your AWS credentials set as environment variables