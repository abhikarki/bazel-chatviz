import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
)

def generate_presigned_post(key: str, content_type: str, max_size: int, expires_in: int = 300) -> dict:
    # Generate a presigned URL for POST upload to a fixed S3 key
    # we enforce conditions for file type and size for the client's uploads to s3.
    return _s3_client.generate_presigned_post(
        Bucket=settings.s3_bucket,
        key=key,
        Fields={
            "Content-Type": content_type,
        },
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 0, max_size],
        ],
        ExpiresIn = expires_in,
    )


def generate_presigned_get(key: str, expires_in: int = 300) -> str:
    return _s3_client.generate_presigned_url(
        ClientMethod = "get_object",
        Params ={"Bucket": settings.s3_bucket, "Key": key},
        ExpiresIn=expires_in,
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
