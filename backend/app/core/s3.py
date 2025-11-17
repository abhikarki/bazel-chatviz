import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
)

def generate_presigned_put_url(key: str, content_type: str, expires_in: int = 300) -> str:
    # Generate a presigned URL for PUT upload to a fixed S3 key
    return _s3_client.generate_presigned_url(
        ClientMethod = "put_object",
        Params = {
            "Bucket": settings.s3_bucket,
            "key": key,
            "ContentType": content_type,
        },
        ExpiresIn = expires_in,
    )

def object_exists(key: str) -> bool:
    # check existence of an s3 object via head request
    try:
        _s3_client.head_object(Bucket=settings.s3_bucket, key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "403", "400", "NoSuchKey"):
            return False
        raise
