import os
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from scripts.utils.config_loader import get

# Configure logging
logger = logging.getLogger(__name__)

# Get S3 configuration with fallbacks
# First try environment variables
_bucket = os.getenv("S3_BUCKET_NAME")
if _bucket:
    logger.info(f"Using S3 bucket from environment variable: {_bucket}")
else:
    # Fall back to config.json
    _bucket = get("s3", {}).get("bucket_name")
    if _bucket:
        logger.info(f"Using S3 bucket from config.json: {_bucket}")
    else:
        logger.warning("S3 bucket name not found in environment variables or config")

# Get region with fallbacks
_region = os.getenv("AWS_DEFAULT_REGION")
if _region:
    logger.info(f"Using AWS region from environment variable: {_region}")
else:
    # Fall back to config.json
    _region = get("s3", {}).get("region", "us-west-2")
    logger.info(f"Using AWS region from config.json: {_region}")

# Get AWS credentials with fallbacks - check multiple environment variable names for compatibility
# First try standard AWS environment variable names (case-sensitive)
_aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
_aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

# Log which source is being used for credentials
if _aws_access_key and _aws_secret_key:
    logger.info("Using AWS credentials from standard environment variables")
else:
    # Try alternate environment variable names that might be used in Render
    _aws_access_key = os.getenv("AWS_access_key_id") or os.getenv("aws_access_key_id")
    _aws_secret_key = os.getenv("AWS_secret_access_key") or os.getenv("aws_secret_access_key")

    if _aws_access_key and _aws_secret_key:
        logger.info("Using AWS credentials from alternate environment variables")
    else:
        # Fall back to config.json
        _aws_access_key = get("s3", {}).get("access_key_id")
        _aws_secret_key = get("s3", {}).get("secret_access_key")

        if _aws_access_key and _aws_secret_key:
            logger.info("Using AWS credentials from config.json")

# Log credential information (safely)
if _aws_access_key:
    logger.info(f"Using AWS access key: {_aws_access_key[:4]}{'*' * 16}")
else:
    logger.warning("AWS access key not found in environment variables or config")

if _aws_secret_key:
    logger.info(f"Using AWS secret key: {'*' * 20}")
else:
    logger.warning("AWS secret key not found in environment variables or config")

logger.info(f"Using S3 bucket: {_bucket}")
logger.info(f"Using AWS region: {_region}")

# Initialize S3 client with credentials if available
if _aws_access_key and _aws_secret_key:
    logger.info("Initializing S3 client with explicit credentials")
    _s3 = boto3.client(
        "s3",
        region_name=_region,
        aws_access_key_id=_aws_access_key,
        aws_secret_access_key=_aws_secret_key
    )
else:
    # Fall back to environment variables or AWS configuration files
    logger.warning("No explicit credentials found, falling back to boto3 default credential chain")
    _s3 = boto3.client("s3", region_name=_region)

def upload_to_s3(local_path: str) -> bool:
    """
    Uploads the given file to s3://<bucket>/paperless/<filename>.
    Returns True if successful, False otherwise.
    """
    # Validate bucket name
    if not _bucket:
        logger.error("S3 bucket name not configured. Set S3_BUCKET_NAME environment variable")
        return False

    key = f"paperless/{os.path.basename(local_path)}"
    try:
        _s3.upload_file(local_path, _bucket, key)
        logger.info(f"✔ Uploaded {local_path} to s3://{_bucket}/{key}")
        return True
    except NoCredentialsError:
        logger.error("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables")
        return False
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == 'InvalidAccessKeyId':
            logger.error(f"✘ Failed to upload {local_path}: Invalid AWS Access Key ID. Please check your AWS credentials.")
            logger.error(f"  Current Access Key ID: {_aws_access_key[:4]}{'*' * 16 if _aws_access_key else 'Not Set'}")
            logger.error(f"  Bucket: {_bucket}")
            logger.error(f"  Error details: {e}")
        elif error_code == 'NoSuchBucket':
            logger.error(f"✘ Failed to upload {local_path}: The S3 bucket '{_bucket}' does not exist.")
            logger.error(f"  Please create the bucket or check the bucket name in your configuration.")
            logger.error(f"  Error details: {e}")
        else:
            logger.error(f"✘ Failed to upload {local_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"✘ Unexpected error uploading {local_path}: {e}")
        logger.error(f"  AWS Access Key ID: {_aws_access_key[:4]}{'*' * 16 if _aws_access_key else 'Not Set'}")
        logger.error(f"  Bucket: {_bucket}")
        logger.error(f"  Region: {_region}")
        return False
