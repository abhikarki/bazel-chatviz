from fastapi import APIRouter, UploadFile
from app.tasks.tasks import process_bep_file

router = APIRouter()

@router.post("/")
async def upload_bep(file: UploadFile):
    contents = await file.read()
    path = f"/tmp/{file.filename}"
    with open(path, "wb") as f:
        f.write(contents)
    process_bep_file.delay(path)
    return {"status": "processing", "file":file.filename}
