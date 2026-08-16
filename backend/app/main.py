from fastapi import FastAPI
from pydantic import BaseModel

from backend.app.rag import ask


app = FastAPI(
    title="3GPP Standards RAG Assistant",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    evidence: list[dict]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "3GPP Standards RAG Assistant",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = ask(request.question)

    return {
        "answer": result["answer"],
        "evidence": result["evidence"],
    }