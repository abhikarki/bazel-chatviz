# simple in-memory DB for uploads

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

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
    status: UploadStatus = UploadStatus.UPLOADING
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

# in-memory store for now, will replace with real DB later.
UPLOAD_STORE: Dict[str, UploadRecord] = {}


def create_upload_record(file_id: str, s3_key: str, original_filename: str) -> UploadRecord:
    record = UploadRecord(
        file_id = file_id,
        s3_key = s3_key,
        original_filename = original_filename,
    )
    UPLOAD_STORE[file_id] = record
    return record


def get_upload_record(file_id: str) -> Optional[UploadRecord]:
    return UPLOAD_STORE.get(file_id)


def update_upload_status(file_id: str, status: UploadStatus, error_message: Optional[str] = None):
    record = UPLOAD_STORE.get(file_id)
    if not record:
        return
    record.status = status
    if status in (UploadStatus.COMPLETED, UploadStatus.FAILED):
        record.completed_at = datetime.utcnow()
    if error_message:
        record.error_message = error_message
    