# [DEPRECATED] AWS S3 Configuration for Webhook Server

> **Note**: This document is deprecated and has been replaced by more comprehensive documentation in the docs directory:
> - For S3 configuration, see [docs/s3_configuration.md](docs/s3_configuration.md)
> - For webhook server information, see [docs/webhook.md](docs/webhook.md)

This document explains how to configure the webhook server to use AWS S3 for storing data files.

## Configuration Options

You can configure AWS S3 integration using either environment variables or the `config.json` file.

### Option 1: Using Environment Variables

Set the following environment variables:

```
S3_BUCKET_NAME=your-s3-bucket-name
AWS_DEFAULT_REGION=your-aws-region
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Option 2: Using config.json

Edit the `scripts/config.json` file and update the S3 section:

```json
"s3": {
  "bucket_name": "your-s3-bucket-name",
  "region": "your-aws-region",
  "access_key_id": "your-access-key",
  "secret_access_key": "your-secret-key"
}
```

## AWS S3 Setup

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

3. **Configure CORS (if needed)**:
   If you're accessing the files from a web application, you may need to configure CORS for your bucket:

   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": []
     }
   ]
   ```

## Troubleshooting

If you encounter issues with S3 uploads:

1. **Check Credentials**: Ensure your AWS credentials are correct and have the necessary permissions
2. **Check Bucket Name**: Verify the S3 bucket name is correct and the bucket exists
3. **Check Region**: Make sure the AWS region is correct
4. **Check Logs**: The application logs will contain detailed error messages if S3 uploads fail

## Testing S3 Configuration

To test if your S3 configuration is working:

1. Start the webhook server
2. Check the logs for any S3-related errors
3. Trigger a webhook event
4. Verify that files are uploaded to your S3 bucket in the `paperless/` prefix
