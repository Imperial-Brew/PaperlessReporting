# S3 Configuration Fix

## Issue Identified

The webhook server was encountering errors when trying to upload data to AWS S3 due to invalid AWS credentials. The specific error was:

```
An error occurred (InvalidAccessKeyId) when calling the PutObject operation: The AWS Access Key Id you provided does not exist in our records.
```

This indicates that the AWS Access Key ID being used was not valid or did not have the necessary permissions to upload to the S3 bucket.

## Changes Made

1. **Improved AWS Credentials Loading**:
   - Updated the credential loading logic to better handle different environment variable names
   - Added more detailed logging to show which source is being used for credentials
   - Improved error handling to provide more context when errors occur

2. **Updated Bucket Name**:
   - Changed the bucket name in config.json to match the one being used in production ("athena-paperless-csvs")
   - Added better logging for bucket name source

3. **Added Test Script**:
   - Created `scripts/test_s3_config.py` to test S3 configuration without triggering a webhook

## How to Fix

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

## AWS S3 Setup

If you need to create a new AWS S3 bucket and IAM user:

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

3. **Update Environment Variables**:
   - Add the new credentials to your Render environment variables

## Troubleshooting

If you continue to experience issues:

1. Check the logs for detailed error messages
2. Verify that the environment variables are set correctly in Render
3. Make sure the S3 bucket exists and is accessible
4. Ensure the IAM user has the necessary permissions
5. Try running the test script locally with your AWS credentials set as environment variables
