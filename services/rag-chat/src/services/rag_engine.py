import os
import uuid
from typing import Optional, Dict, List

from langchain_openai import ChatOpenAI
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_classic.chains import ConversationalRetrievalChain
from langchain_classic.schema import Document
from langchain_community.vectorstores import Weaviate
import weaviate

class RAGEngine:
    def __init__(self):
        self.llm = ChatOpenAI(openai_api_key = os.getenv("OPENAI_API_KEY"), model = "gpt-4o-mini", temperature = 0.1)

        self.sessions: Dict[str, ConversationBufferWindowMemory] = {}

        self.weaviate_client = weaviate.Client(url=os.getenv("WEAVIATE_URL", "http://localhost:8080"))

    def _get_or_create_session(self, session_id: Optional[str]) -> tuple[str, ConversationBufferWindowMemory]:
        if not session_id:
            session_id = uuid.uuid4().hex
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationBufferWindowMemory(
                memory_key = "chat_history",
                return_messages = True,
                k = 10
            )
        return session_id, self.sessions[session_id]
    
    async def query(self, query: str, file_id: Optional[str], session_id: Optional[str]) -> dict:
        session_id, memory = self._get_or_create_session(session_id)

        # getting retriever for file
        retriever = None
        if file_id:
            try:
                vectorstore = Weaviate(
                    client=self.weaviate_client,
                    class_name="Document",
                    text_key="text"
                )
                # Filter to only retrieve objects with the correct file_id
                retriever = vectorstore.as_retriever(
                    search_kwargs={
                        "k": 4,
                        "filters": {
                            "file_id": file_id
                        }
                    }
                )
            except Exception:
                retriever = None

        if not retriever:
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