from fastapi import FastAPI
from app.api.upload import router as upload_router

app = FastAPI(title="Uploader Service", version="1.0.0")

# Attach the router to the main app
app.include_router(upload_router)