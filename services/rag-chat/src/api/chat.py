from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from services.rag_engine import RAGEngine

router = APIRouter(prefix="/api", tags=["chat"])

rag_engine = RAGEngine()

class QueryRequest(BaseModel):
    query: str
    file_id: Optional[str] = None
    session_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    session_id: str

class IndexRequest(BaseModel):
    file_id: str
    s3_key: str

# Chat endpoint
@router.post("/query", response_model=QueryResponse)
async def query_build(request:QueryRequest):
    try:
        result = await rag_engine.query(
            query = request.query,
            file_id = request.file_id,
            session_id = request.session_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    rag_engine.clear_session(session_id)
    return {"status" : "cleared"}