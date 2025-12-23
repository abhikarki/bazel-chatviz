from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import uuid

# Import the celery_app instance from the main application file
from app.celery_app import app
from app.core.s3 import generate_presigned_post, object_exists, generate_presigned_get
from app.core.config import settings
from app.models.uploads import(
    create_upload_record,
    get_upload_record,
    update_upload_status,
    UploadStatus,
)

router = APIRouter(prefix="/upload", tags=["upload"])

# Request and Response schemas

class InitUploadRequest(BaseModel):
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type, e.g. application/json")
    size: int = Field(..., description="File size in bytes")


class InitUploadResponse(BaseModel):
    file_id: str
    url: str        # s3 POST URL
    fields: dict    # form fields that must be sent with the file
    expires_in: int

class CompleteUploadRequest(BaseModel):
    file_id: str

class UploadStatusResponse(BaseModel):
    file_id: str
    status: UploadStatus
    original_filename: str
    error_message: str | None = None

class ArtifactURLsResponse(BaseModel):
    file_id: str
    summary_url: str | None = None
    graph_url: str | None = None
    resource_usage_url: str | None = None



@router.post("/init", response_model=InitUploadResponse, status_code=status.HTTP_201_CREATED)
async def init_upload(req: InitUploadRequest):
    # Some validation we perform
    max_size = 20_000_000     # 20MB
    if req.size > max_size:
        raise HTTPException(status_code=413, detail="File too large")
    
    allowed_types = {"application/json", "application/octet-stream"}
    if req.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail=f"Unsupported content type: {req.content_type}"
        )
    
    file_id = uuid.uuid4().hex
    # Late we can include user_id here once we set up the auth
    # s3_key = f"bep-files/{user_id}/{file_id}.json"
    s3_key = f"bep-files/{file_id}.json"

    presigned = generate_presigned_post(
        Key=s3_key,
        content_type=req.content_type,
        max_size=max_size,
        expires_in=300,  #seconds
    )

    #store metadata
    createdRecord = create_upload_record(
        file_id=file_id,
        s3_key=s3_key,
        original_filename=req.filename,
        content_type = req.content_type,
        max_size = max_size,
        )
    
    

    return InitUploadResponse(
        file_id = file_id,
        url = presigned["url"],
        fields = presigned["fields"],
        expires_in = 300,
    )

# when client says upload is done, we will assign Celery job
@router.post("/complete", status_code=status.HTTP_202_ACCEPTED)
async def complete_upload(req: CompleteUploadRequest):
    record = get_upload_record(req.file_id)
    if not record:
        raise HTTPException(status_code = 404, detail = "Unknown file_id")
    
    # Verify that the file has been actually uploaded in s3
    if not object_exists(record.s3_key):
        raise HTTPException(status_code=400, detail="File not found in storage yet")
    
    # Update status and enqueue Celery job by sending a task by name
    # The task "src.tasks.tasks.process_bep_file" is discovered by the celery-worker.
    update_upload_status(req.file_id, UploadStatus.PROCESSING)
    taskRes = app.send_task(
        "process_bep_file",
        args=[req.file_id, record.s3_key],
    )
    print("the task id is : ", taskRes)   # debugging if the task was queued properly

    return {"status": "processing", "file_id": req.file_id}



# allowing frontend to poll
@router.get("/status/{file_id}", response_model=UploadStatusResponse)
async def get_upload_status(file_id: str):
    record = get_upload_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Unknown file_id")
    
    return UploadStatusResponse(
        file_id=record.file_id,
        status=record.status,
        original_filename=record.original_filename,
        error_message=record.error_message,
    )


@router.get("/artifacts/{file_id}", response_model=ArtifactURLsResponse)
async def get_artifact_urls(file_id: str):
    record = get_upload_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Unknown file_id")
    
    if record.status != UploadStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="File not processed")
    
    # Celery wrote all artifacts to:
    # processed/{file_id}/summary.json
    # processed/{file_id}/graph.json
    # processed/{file_id}/resource-usage.json

    base = record.output_json_url

    files = {
        "summary_url":base + "summary.json",
        "graph_url": base + "graph.json",
        "resource_usage_url": base + "resource-usage.json",
    }

    urls = {}
    for name, s3_key in files.items():
        urls[name] = generate_presigned_get(s3_key)

    return ArtifactURLsResponse(file_id=file_id, **urls)
