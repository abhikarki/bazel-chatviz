from celery import Celery
import boto3
import json
from app.core.config import settings
from app.models.uploads import update_upload_status, UploadStatus

app = Celery("tasks", broker="pyamqp://guest@rabbitmq//")

_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
)

@app.task
def process_bep_file(file_id: str, s3_key: str):
    try:
        #1. download from s3
        obj = _s3_client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        raw = obj["Body"].read()

        ## TODO: logic for processing the file


        update_upload_status(file_id, UploadStatus.COMPLETED)
    except Exception as e:
        update_upload_status(file_id, UploadStatus.FAILED, error_message=str(e))
        raise
