import os
import logging
import sys
from pathlib import Path

# Add the parent directory to sys.path to allow imports from scripts.utils
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from scripts.utils.s3_helpers import upload_to_s3
from scripts.utils.config_loader import get

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_s3_config():
    """Test the S3 configuration by uploading a test file."""
    logger.info("=== Testing S3 Configuration ===")

    # Get S3 configuration
    bucket_name = os.getenv("S3_BUCKET_NAME")
    if not bucket_name:
        bucket_name = get("s3", {}).get("bucket_name")

    region = os.getenv("AWS_DEFAULT_REGION")
    if not region:
        region = get("s3", {}).get("region", "us-west-2")

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    if not access_key:
        access_key = get("s3", {}).get("access_key_id")

    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if not secret_key:
        secret_key = get("s3", {}).get("secret_access_key")

    logger.info(f"S3 Bucket: {bucket_name}")
    logger.info(f"S3 Region: {region}")
    logger.info(f"Access Key: {access_key[:4] + '...' if access_key else 'Not Set'}")
    logger.info(f"Secret Key: {'Set' if secret_key else 'Not Set'}")

    # Create a test file
    test_file = "s3_test.txt"
    with open(test_file, "w") as f:
        f.write("This is a test file for S3 upload.")

    logger.info(f"Created test file: {test_file}")

    # Upload the test file to S3
    result = upload_to_s3(test_file)

    if result:
        logger.info("✅ S3 configuration is working correctly!")
        logger.info(f"Test file uploaded to s3://{bucket_name}/paperless/{test_file}")
    else:
        logger.error("❌ S3 configuration is not working correctly.")
        logger.error("Please check your S3 configuration and try again.")

    # Clean up the test file
    try:
        os.remove(test_file)
        logger.info(f"Removed test file: {test_file}")
    except Exception as e:
        logger.warning(f"Failed to remove test file: {e}")

    return result

if __name__ == "__main__":
    test_s3_config()
