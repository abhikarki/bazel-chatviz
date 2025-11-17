from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
import uuid

from app.core.s3 import generate_presigned_put_url, object_exists
from app.core.config import settings
from app.models.uploads import(
    create_upload_record,
    get_upload_record,
    update_upload_status,
    UploadStatus,
)
from app.tasks.tasks import process_bep_file

router = APIRouter(prefix="/upload", tags=["upload"])

# Request and Response schemas

class InitUploadRequest(BaseModel):
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type, e.g. application/json")
    size: int = Field(..., description="File size in bytes")


class InitUploadResponse(BaseModel):
    file_id: str
    upload_url: str
    expires_in: int

class CompleteUploadRequest(BaseModel):
    file_id: str

class UploadStatusResponse(BaseModel):
    file_id: str
    status: UploadStatus
    original_filename: str
    error_message: str | None = None


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
    s3_key = f"bef-files/{file_id}.json"

    presigned_url = generate_presigned_put_url(
        key=s3_key,
        content_type=req.content_type,
        expires_in=300,  #seconds
    )

    #store metadata
    create_upload_record(file_id=file_id, s3_key=s3_key, original_filename=req.filename)

    return InitUploadResponse(
        file_id = file_id,
        upload_url = presigned_url,
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
    
    # Update status and enqueue Celery job
    update_upload_status(req.file_id, UploadStatus.PROCESSING)
    process_bep_file.delay(file_id=req.file_id, s3_key=record.s3_key)

    return {"status": "processing", "file_id": req.file_id}



# allowing frontend to poll
@router.get("/status/{file_id}", response_model=UploadStatusResponse)
async def get_upload_record(file_id: str):
    record = get_upload_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="Unknown file_id")
    
    return UploadStatusResponse(
        file_id=record.file_id,
        status=record.status,
        original_filename=record.original_filename,
        error_message=record.error_message,
    )
