from dotenv import load_dotenv

load_dotenv()

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router

from telemetry import setup_telemetry, instrument_fastapi

tracer, meter = setup_telemetry(
    service_name = "rag-chat",
    service_version = "1.0.0",
)

query_counter = meter.create_counter(
    name = "chat_queries_total",
    description = "Total number of chat queries",
    unit = "1",
)

llm_latency_histogram = meter.create_histogram(
    name = "llm_response_time_second",
    description = "LLM response time",
    unit = "s",
)

vector_search_histogram = meter.create_histogram(
    name = "vector_search_time_second",
    description = "vector search latency",
    unit = "s",
)

app = FastAPI(title="RAG Chat Service", version="1.0.0")

instrument_fastapi(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

@app.get("/health")
async def health():
    return {"status" : "ok", "service": "rag-chat"}