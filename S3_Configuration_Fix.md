# S3 Configuration Fix

## Issue Identified

The webhook server was encountering errors when trying to upload data to AWS S3 due to improper S3 configuration in the `config.json` file. The configuration had placeholder values for the bucket name and empty values for the AWS credentials.

## Changes Made

1. Updated the S3 configuration in `scripts/config.json` with more meaningful placeholder values:
   - Set `bucket_name` to "paperless-webhook-data"
   - Added placeholder text for `access_key_id` and `secret_access_key` to make it clear that these need to be replaced with real values

## Required Actions

To properly configure S3 for the webhook server, you need to:

1. **Option 1: Update config.json**
   - Edit `scripts/config.json` and replace the placeholder values with your actual AWS S3 configuration:
     ```json
     "s3": {
       "bucket_name": "your-actual-bucket-name",
       "region": "your-aws-region",
       "access_key_id": "your-actual-access-key",
       "secret_access_key": "your-actual-secret-key"
     }
     ```

2. **Option 2: Set Environment Variables**
   - Set the following environment variables:
     ```
     S3_BUCKET_NAME=your-actual-bucket-name
     AWS_DEFAULT_REGION=your-aws-region
     AWS_ACCESS_KEY_ID=your-actual-access-key
     AWS_SECRET_ACCESS_KEY=your-actual-secret-key
     ```

## AWS S3 Setup

If you haven't already set up an AWS S3 bucket, follow these steps:

1. **Create an S3 Bucket**:
   - Log in to the AWS Management Console
   - Navigate to S3
   - Create a new bucket with a unique name
   - Note the bucket name for configuration

2. **Create IAM User with S3 Access**:
   - Navigate to IAM in the AWS Console
   - Create a new user with programmatic access
   - Attach the `AmazonS3FullAccess` policy (or create a custom policy with more limited permissions)
   - Save the Access Key ID and Secret Access Key

## Testing

After configuring S3, you can test the configuration using the provided test script:

```
python scripts/test_s3_config.py
```

This script will:
1. Get the S3 configuration from environment variables or the config.json file
2. Create a test file
3. Attempt to upload the test file to S3
4. Report whether the upload was successful
5. Clean up the test file

You can also test the webhook server by:

1. Restarting the webhook server
2. Checking the logs for any S3-related errors
3. Triggering a webhook event (using one of the test scripts)
4. Verifying that files are uploaded to your S3 bucket in the `paperless/` prefix

For more detailed information on S3 configuration, refer to the [Webhook_S3_Setup.md](Webhook_S3_Setup.md) file.
