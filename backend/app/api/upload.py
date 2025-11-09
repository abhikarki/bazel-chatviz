from fastapi import APIRouter, UploadFile, File, HTTPException
from app.tasks.tasks import process_bep_file
import os
import uuid
import aiofiles
from pathlib import Path

router = APIRouter()
logger = logging.getLogger("bazel-chatviz")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok = True)

@router.post("/")
async def upload_bep(file: UploadFile = File(...)):
    # Accept a BEP file, save it temporarily and trigger
    # a celery task to process it into a vector database

    # validate file type
    if not file.filename.endswith(".bep") and not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be .bep or .json")
    
    # generate unique path
    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}_{file.filename}"
    path = os.path.join(UPLOAD_DIR, safe_filename)

    
    
    try:
        with open(path, "wb") as f:
            while chunk := await file.read(1024*1024):
                f.write(chunk)

        task = process_bep_file.delay(path)
        logger.info(f"Queued BEP file for processing: {safe_filename}, task_id={task.id}")

        return {"status": "queued", "task_id": task.id, "file": safe_filename}
    
    except Exception as e:
        logger.exception(f"Error uploading BEP file : {e}")
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to proces upload"
        )