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
            
        )