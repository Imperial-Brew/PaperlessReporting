import os
import boto3
from botocore.exceptions import ClientError

_bucket = os.getenv("S3_BUCKET_NAME")
_region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
_s3 = boto3.client("s3", region_name=_region)

def upload_to_s3(local_path: str) -> bool:
    """
    Uploads the given file to s3://<bucket>/paperless/<filename>.
    Returns True if successful, False otherwise.
    """
    key = f"paperless/{os.path.basename(local_path)}"
    try:
        _s3.upload_file(local_path, _bucket, key)
        print(f"✔ Uploaded {local_path} to s3://{_bucket}/{key}")
        return True
    except ClientError as e:
        print(f"✘ Failed to upload {local_path}: {e}")
        return False
