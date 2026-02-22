import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.upload import router as upload_router

from app.telemetry import setup_telemetry, instrument_fastapi

tracer, meter = setup_telemetry(
    service_name = "uploader",
    service_version = "1.0.0",
)

# custom metrics
upload_counter = meter.create_counter(
    name = "bep_uploads_total",
    description = "Total number of BEP file uploads",
    unit = "1",
)

upload_size_histogram = meter.create_histogram(
    name = "bep_upload_size_bytes",
    description = "Size of uploaded BEP files",
    unit = "bytes",
)

app = FastAPI(title = "Uploader Service", version = "1.0.0")

instrument_fastapi(app)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3004",
    "http://127.0.0.1:3004",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*'],
)

app.include_router(upload_router)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "uploader"}

logger = logging.getLogger(__name__)