import redis
from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Optional
import json
from fastapi.encoders import jsonable_encoder

status_redis = redis.Redis(host="localhost", port=6380, db=0, decode_responses = True)

class UploadStatus(str, Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class UploadRecord:
    file_id: str
    s3_key: str
    original_filename: str
    content_type: str
    max_size: int
    status: UploadStatus = UploadStatus.UPLOADING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    output_json_url: Optional[str] = None

# # in-memory store for now, will replace with real DB later.
# UPLOAD_STORE: Dict[str, UploadRecord] = {}

def _upload_key(file_id: str) -> str:
    return f"upload:{file_id}"


# create and upload entry when upload/init is called
def create_upload_record(file_id: str, s3_key: str, original_filename: str, content_type: str, max_size: int) -> UploadRecord:
    record = UploadRecord(
        file_id = file_id,
        s3_key = s3_key,
        original_filename = original_filename,
        content_type = content_type,
        max_size = max_size,
    )
    # UPLOAD_STORE[file_id] = record
    status_redis.set(_upload_key(file_id), json.dumps(jsonable_encoder(record)))
    return record

# Retrieve metadata for particular upload
def get_upload_record(file_id: str) -> Optional[UploadRecord]:
    data = status_redis.get(_upload_key(file_id))
    if not data:
        return None
    d = json.loads(data)

    #converting timestamps back to datetime
    if d.get("created_at"):
        d["created_at"] = datetime.fromisoformat(d["created_at"])

    if d.get("completed_at"):
        d["completed_at"] = datetime.fromisoformat(d["completed_at"])
    
    # for enum
    d["status"] = UploadStatus(d["status"])

    return UploadRecord(**d)


# updates the lifecycle of upload during processing.
def update_upload_status(file_id: str, status: UploadStatus, error_message: Optional[str] = None, output_location: Optional[str] = None):
    # record = UPLOAD_STORE.get(file_id)
    record = get_upload_record(file_id)
    if not record:
        return
    record.status = status
    if status in (UploadStatus.COMPLETED, UploadStatus.FAILED):
        record.completed_at = datetime.utcnow()
    if error_message:
        record.error_message = error_message
    if output_location:
        record.output_json_url = output_location
    status_redis.set(_upload_key(file_id), json.dumps(jsonable_encoder(record)))
    