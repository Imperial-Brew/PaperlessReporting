import os
import boto3
import logging
from botocore.exceptions import ClientError, NoCredentialsError
from scripts.utils.config_loader import get

# Configure logging
logger = logging.getLogger(__name__)

# Get S3 configuration with fallbacks
_bucket = os.getenv("S3_BUCKET_NAME", get("s3", {}).get("bucket_name"))
_region = os.getenv("AWS_DEFAULT_REGION", get("s3", {}).get("region", "us-west-2"))

# Get AWS credentials with fallbacks
_aws_access_key = os.getenv("AWS_ACCESS_KEY_ID", get("s3", {}).get("access_key_id"))
_aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY", get("s3", {}).get("secret_access_key"))

# Initialize S3 client with credentials if available
if _aws_access_key and _aws_secret_key:
    _s3 = boto3.client(
        "s3",
        region_name=_region,
        aws_access_key_id=_aws_access_key,
        aws_secret_access_key=_aws_secret_key
    )
else:
    # Fall back to environment variables or AWS configuration files
    _s3 = boto3.client("s3", region_name=_region)

def upload_to_s3(local_path: str) -> bool:
    """
    Uploads the given file to s3://<bucket>/paperless/<filename>.
    Returns True if successful, False otherwise.
    """
    # Validate bucket name
    if not _bucket:
        logger.error("S3 bucket name not configured. Set S3_BUCKET_NAME environment variable or add s3.bucket_name to config.json")
        return False

    key = f"paperless/{os.path.basename(local_path)}"
    try:
        _s3.upload_file(local_path, _bucket, key)
        logger.info(f"✔ Uploaded {local_path} to s3://{_bucket}/{key}")
        return True
    except NoCredentialsError:
        logger.error("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables or add s3.access_key_id and s3.secret_access_key to config.json")
        return False
    except ClientError as e:
        logger.error(f"✘ Failed to upload {local_path}: {e}")
        return False
    except Exception as e:
        logger.error(f"✘ Unexpected error uploading {local_path}: {e}")
        return False
