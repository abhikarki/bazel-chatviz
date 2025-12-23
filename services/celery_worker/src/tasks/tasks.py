from celery import Celery
import os
import boto3
import json
import logging
from botocore.exceptions import BotoCoreError, ClientError
from src.core.config import settings
from src.models.uploads import update_upload_status, UploadStatus
from src.services.bep_parser import BEPParser

os.environ['FORKED_BY_MULTIPROCESSING'] = '1'
log = logging.getLogger(__name__)

app = Celery("src", broker=settings.celery_broker_url, backend=settings.celery_result_backend)


_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
    endpoint_url = "http://localhost:4566"
)

# register the task with unique name - the path
@app.task(name="process_bep_file", bind=True, max_retries=1, default_retry_delay=5)
def process_bep_file(self, file_id: str, s3_key: str) -> None:
    print("here")
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
        # the export functions return bytes
        processed_summary = parser.export_summary()
        processed_graph = parser.export_graph()
        processed_resource_usage = parser.export_resource_usage()

        base_key = f"processed/{file_id}/"

        # Putting the results back to s3
        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "summary.json",
            Body = processed_summary,
            ContentType = "application/json",
        )

        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "graph.json",
            Body = processed_graph,
            ContentType = "application/json",
        )

        _s3_client.put_object(
            Bucket = settings.s3_bucket,
            Key = base_key + "resource-usage.json",
            Body = processed_resource_usage,
            ContentType = "application/json",
        )


        update_upload_status(file_id, UploadStatus.COMPLETED, output_location=base_key)
        log.info("Processed BEP file %s -> %s", s3_key, base_key)

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