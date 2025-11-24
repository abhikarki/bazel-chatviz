from celery import Celery
import boto3
import json
import logging
from botocore.exceptions import BotoCoreError, ClientError
from app.core.config import settings
from app.models.uploads import update_upload_status, UploadStatus
from app.services.bep_parser import BEPParser

log = logging. getLogger(__name__)

app = Celery("tasks", broker = getattr(settings, "celery_broker_url", "pyamqp://guest@rabbitmq//"))


_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
)

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_bep_file(self, file_id: str, s3_key: str) -> None:
    try:
        update_upload_status(file_id, UploadStatus.PROCESSING)

        # contact s3 for the file
        obj = _s3_client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
        # extract the streaming object from the S3 response. This object is a file-like handle
        # that starts downloading the data only when the code iterates over it. 
        body = obj["Body"]

        parser = BEPParser()

        # lines is a generator
        def lines():
            for raw_line in body.iter_lines(chunk_size=65536):
                # skip blank lines
                if not raw_line:
                    continue
                try:
                    # decode the bytes into a string using standard UTF-8 encoding, which is default for JSON
                    line = raw_line.decode("utf-8")
                except Exception:
                    # fallback when decoding fails
                    line = raw_line.decode("latin-1", errors="ignore")
                yield line    # pass the decoded string line back to the function that called the generator.
        
        parser.parse_stream(lines())


        # RAG processing to be implemented.
        # try:
        #     if getattr(settings, "enable_rag_processing", True):
        #         parser.rag_processor.process_bep_data(parser.events)
        # except Exception as rag_error:
        #     log.exception("RAG processing failed; continuing: %s", rag_error)

        
        # Build summary
        processed_summary = parser.export_summary()
        processed_graph = parser.export_graph()
        processed_resource_usage = parser.export_resource_usage()

        base_key = f"processed/{file_id}/"

        # Putting the results back to s3
        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "summary.json",
            Body = json.dumps(processed_summary).encode("utf-8"),
            ContentType = "application/json",
        )

        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "graph.json",
            Body = json.dumps(processed_graph).encode("utf-8"),
            ContentType = "application/json",
        )

        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "resource-usage.json",
            Body = json.dumps(processed_resource_usage).encode("utf-8"),
            ContentType = "application/usage",
        )


        update_upload_status(file_id, UploadStatus.COMPLETED, output_location=base_key)
        log.info("Processed BEP file %s", s3_key, base_key)

    except(BotoCoreError, ClientError) as s3_err:
        log.exception("s3 error while processing %s", s3_key, s3_err)
        try:
            raise self.retry(exc=s3_err)
        except Exception:
            update_upload_status(file_id, UploadStatus.FAILED, error_message=str(s3_err))
            raise
    
    except Exception as e:
        log.exception("Fatal error processing %s", s3_key, e)
        update_upload_status(file_id, UploadStatus.FAILED, error_message=str(e))
        raise