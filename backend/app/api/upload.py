from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.tasks.tasks import process_bep_file
from pathlib import Path
import aiofiles
import uuid

router = APIRouter()

TEMP_DIR = Path("/tmp/bep_uploads")
TEMP_DIR.mkdir(parents=True, exist_ok=True)  # fix the comma typo

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def upload_bep(file: UploadFile = File(...)):
    """
    Accept a BEP file upload, persist it to a temp directory, and enqueue
    a Celery task to process it.
    """
    # Optional: basic content-type/extension guardrail
    # (Adjust these to what your BEP actually is.)
    allowed_types = {"application/octet-stream", "application/json"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=415, detail=f"Unsupported content type: {file.content_type}"
        )

    # Always generate a unique, safe filename; keep original separately
    original_name = Path(file.filename).name if file.filename else "upload.bin"
    unique_name = f"{uuid.uuid4().hex}__{original_name}"
    temp_path = TEMP_DIR / unique_name
    tmp_staging = TEMP_DIR / (unique_name + ".part")  # write-then-move

    try:
        # Stream to disk in chunks (1 MiB)
        async with aiofiles.open(tmp_staging, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                await f.write(chunk)

        # Atomic move into place
        tmp_staging.replace(temp_path)

        # Enqueue background processing
        process_bep_file.delay(str(temp_path), original_name)

        return {
            "status": "processing",
            "file_saved_as": temp_path.name,
            "original_filename": original_name,
            "message": "Upload received. Processing has begun.",
        }

    except HTTPException:
        # re-raise explicit HTTP errors
        raise
    except Exception as e:
        # Cleanup partial files if something failed
        try:
            if tmp_staging.exists():
                tmp_staging.unlink(missing_ok=True)
        finally:
            raise HTTPException(status_code=500, detail="Failed to process file.") from e
    finally:
        await file.close()
