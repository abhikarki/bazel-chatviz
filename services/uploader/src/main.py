from fastapi import FastAPI
from api.upload import router as upload_router

app = FastAPI(title="Uploader Service", version="1.0.0")

app.include_router(upload_router)