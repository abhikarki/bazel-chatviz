from celery import Celery
import os
import boto3
import json
import time
import logging
from botocore.exceptions import BotoCoreError, ClientError

from opentelemetry import trace
from opentelemetry.instrumentation.celery import CeleryInstrumentor

from src.core.config import settings
from src.models.uploads import update_upload_status, UploadStatus
from src.services.bep_parser import BEPParser

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Weaviate
import weaviate

os.environ['FORKED_BY_MULTIPROCESSING'] = '1'

logging.basicConfig(level = logging.INFO)
log = logging.getLogger(__name__)

from src.telemetry import setup_telemetry
tracer, meter = setup_telemetry(
    service_name = "celery-worker",
    service_version = "1.0.0",
)

task_counter = meter.create_counter(
    name = "celery_tasks_total",
    description = "Total Celery tasks by name and status",
    unit = "1",
)

task_duration_histogram = meter.create_histogram(
    name = "celery_task_duration_seconds",
    description = "Celery task execution time",
    unit = "s",
)

bep_parsing_histogram = meter.create_histogram(
    name = "bep_parsing_time_seconds",
    description = "BEP file parsing duration",
    unit = "s",
)

app = Celery("src", broker=settings.celery_broker_url, backend=settings.celery_result_backend)

CeleryInstrumentor().instrument()

# embedding client and vector DB client (Weaviate)
embedding_client = OpenAIEmbeddings(openai_api_key=settings.openai_api_key)
weaviate_client = weaviate.Client("http://localhost:8080")


_s3_client = boto3.client(
    "s3",
    region_name = settings.aws_region,
    aws_access_key_id = settings.aws_access_key_id,
    aws_secret_access_key = settings.aws_secret_access_key,
    endpoint_url = "http://localhost:4566"
)

# register the task with unique name - the path@app.task(name="process_bep_file", bind=True, max_retries=1, default_retry_delay=5)
def process_bep_file(self, file_id: str, s3_key: str) -> None:
    task_start = time.time()
    
    with tracer.start_as_current_span("process_bep_file") as span:
        span.set_attribute("task.file_id", file_id)
        span.set_attribute("task.s3_key", s3_key)
        
        logger.info(f"Starting BEP processing: file_id={file_id}")
        
        try:
            update_upload_status(file_id, UploadStatus.PROCESSING)

            # Download from S3 (auto-instrumented via botocore)
            with tracer.start_as_current_span("s3_download") as s3_span:
                obj = _s3_client.get_object(Bucket=settings.s3_bucket, Key=s3_key)
                body = obj["Body"]
                s3_span.set_attribute("s3.bucket", settings.s3_bucket)
                s3_span.set_attribute("s3.key", s3_key)

            # Parse BEP file
            with tracer.start_as_current_span("parse_bep") as parse_span:
                parse_start = time.time()
                
                parser = BEPParser()

                def lines():
                    for raw_line in body.iter_lines(chunk_size=65536):
                        if not raw_line:
                            continue
                        try:
                            line = raw_line.decode("utf-8")
                        except Exception:
                            line = raw_line.decode("latin-1", errors="ignore")
                        yield line
                
                parser.parse_stream(lines())
                
                parse_duration = time.time() - parse_start
                parse_span.set_attribute("parse.duration_seconds", parse_duration)
                bep_parsing_histogram.record(parse_duration, {"file_id": file_id})

            # Export results
            with tracer.start_as_current_span("export_results") as export_span:
                processed_summary = parser.export_summary()
                processed_graph = parser.export_graph()
                processed_resource_usage = parser.export_resource_usage()

            # Upload to S3
            with tracer.start_as_current_span("s3_upload_results") as upload_span:
                base_key = f"processed/{file_id}/"
                
                _s3_client.put_object(
                    Bucket=settings.s3_bucket,
                    Key=base_key + "summary.json",
                    Body=processed_summary,
                    ContentType="application/json",
                )

                _s3_client.put_object(
                    Bucket=settings.s3_bucket,
                    Key=base_key + "graph.json",
                    Body=processed_graph,
                    ContentType="application/json",
                )

                _s3_client.put_object(
                    Bucket=settings.s3_bucket,
                    Key=base_key + "resource-usage.json",
                    Body=processed_resource_usage,
                    ContentType="application/json",
                )
                
                upload_span.set_attribute("s3.files_uploaded", 3)

            # Generate embeddings
            with tracer.start_as_current_span("generate_embeddings") as embed_span:
                # ... existing embedding code ...
                pass

            # Update status
            update_upload_status(file_id, UploadStatus.COMPLETED)
            
            task_duration = time.time() - task_start
            task_counter.add(1, {"task_name": "process_bep_file", "status": "success"})
            task_duration_histogram.record(task_duration, {"task_name": "process_bep_file"})
            
            logger.info(f"BEP processing completed: file_id={file_id}, duration={task_duration:.2f}s")
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            span.record_exception(e)
            
            task_counter.add(1, {"task_name": "process_bep_file", "status": "failed"})
            update_upload_status(file_id, UploadStatus.FAILED, error_message=str(e))
            
            logger.error(f"BEP processing failed: file_id={file_id}, error={e}")
            raise