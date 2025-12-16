import os
import json
import uuid
import boto3
from typing import Optional, Dict, List
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import Document

class RAGEngine:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.llm = ChatOpenAI(model = "gpt-4o-mini", temperature = 0.1)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 1000,
            chunk_overlap = 200
        )

        # Currently in memory
        # file_id -> vectorstore
        self.vector_stores: Dict[str, FAISS] = {}    
        self.sessions: Dict[str, ConversationBufferWindowMemory]

        self.s3 = boto3.client("s3")
        self.bucket = os.getenv("S3_BUCKET")

    def _get_or_create_session(self, session_id: Optional[str]) -> tuple[str, ConversationBufferWindowMemory]:
        if not session_id:
            session_id = uuid.uuid4().hex

        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationBufferWindowMemory(
                # using this when passing to prompt
                memory_key = "chat_history",
                return_messages=True,
                # message window, last 10 exchanges
                k=10
            )
        return session_id, self.sessions[session_id]
    
    async def index_build(self, file_id: str, s3_key: str):
        documents = []

        for file_type in ["summary.json", "graph.json", "resource-usage.json"]:
            try:
                obj = self.s3.get_object(Bucket=self.bucket, key=f"{s3_key}{file_type}")
                data = json.loads(obj["Body"].read().decode("utf-8"))

                text = self._json_to_text(data, file_type)
                documents.append(Document(
                    page_context = text,
                    metadata = {"file_id": file_id, "type": file_type}
                ))
            except Exception:
                continue
        if not documents:
            raise ValueError("No data found to index")
        
        chunks = self.text_splitter.split_documents(documents)
        self.vector_stores[file_id] = FAISS.from_documents(chunks, self.embeddings)

    def _json_to_text(self, data: dict, file_type: str) -> str:
        if "summary" in file_type:
            return self._format_summary(data)
        elif "graph" in file_type:
            return self._format_graph(data)
        elif "resource" in file_type:
            return self._format_resources(data)
        return json.dumps(data, indent = 2)
    
    def _format_summary(self, data: dict) -> str:
        lines = ["BUILD SUMMARY: "]
        lines.append(f"Total targets: {data.get('total_targets', 'N/A')}")
        lines.append(f"Successful: {data.get('successful', 'N/A')}")
        lines.append(f"Failed: {data.get('failed', 'N/A')}")
        lines.append(f"Actions executed: {data.get('action_count', 'N/A')}")

        if "failed_targets" in data:
            lines.append("Failed targets: " + ", ".join(data["failed_targets"]))
        return "\n".join(lines)
    
    def _format_graph(self, data: dict) -> str:
        lines = ["DEPENDENCY GRAPH"]
        for node in data.get("nodes", []):
            deps = ", ".join(node.get("dependencies", [])) or "none"
            lines.append(f"Target {node.get('label')} ({node.get('kind', 'unknown')}) depends on {deps}")
        return "\n".join(lines)

    def _format_resources(self, data: dict) -> str:
        lines = ["RESOURCE USAGE: "]
        for point in data.get("series", [])[:20]:
            lines.append(f"Time {point.get('time')}: CPU={point.get('cpu')}%, Memory={point.get('memory')}%")
        return "\n".join(lines)
    
    async def query(self, query: str, file_id: Optional[str], session_id: Optional[str]) -> dict:
        session_id, memory = self._get_or_create_session(session_id)

        # if file_id exists
        if file_id and file_id in self.vector_stores:
            retriever = self.vector_stores[file_id].as_retriever(search_kwargs={"k": 4})
        elif self.vector_stores:     # if any file_id exists
            retriever = list(self.vector_stores.values())[-1].as_retriever(search_kwargs={"k": 4})
        else:          # genenral llm query
            response = await self._general_query(query)
            return {"response": response, "sources": None, "session_id": session_id}

        chain = ConversationalRetrievalChain.from_llm(
            llm = self.llm,
            retriever = retriever,
            memory = memory,
            return_source_documents = True
        )

        result = chain.invoke({"question": query})
        sources = [doc.metadata.get("type") for doc in result.get("source_documents", [])]

        return {
            "response": result["answer"],
            "sources": list(set(sources)),
            "session_id": session_id
        }    
    
    async def _general_query(self, query: str) -> str:
        messages = [
            {"role": "system", "content": "You are a Bazel Build analysis assistant. Help users understand Bazel Builds, BEP files, dependencies, and optimization strategies"},
            {"role": "user", "content": query}
        ]
        response = self.llm.invoke(messages)
        return response.content

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

