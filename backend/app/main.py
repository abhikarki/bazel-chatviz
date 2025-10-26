from fastapi import FastAPI
from app.api import upload, graph, chat
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Bazel ChatViz API")

# currently unsafe configuration. Need to list the origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/upload")
app.include_router(graph.router, prefix = "/graph")
app.include_router(chat.router, prefix="/chat")



