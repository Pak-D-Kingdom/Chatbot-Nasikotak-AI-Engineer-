import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.pipeline import ChatPipeline
from src.database import SessionLocal, init_db

# Initialize database
init_db()

# Initialize FastAPI app
app = FastAPI(title="AI Sales Chatbot API")

# Initialize ChatPipeline
pipeline = ChatPipeline()

# Ensure static directory exists
import os
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Models
class ChatRequest(BaseModel):
    session_id: str
    message: str

class Entity(BaseModel):
    quantity: Optional[int] = None
    budget_per_box: Optional[float] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    purchase_intent: str
    entities: dict
    actions: List[str]
    needs_handover: bool
    handover_reason: Optional[str] = None
    whatsapp_link: Optional[str] = None
    lead_status: Optional[str] = None
    rag_sources: Optional[List[str]] = None

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/api/session/new")
async def new_session():
    return {"session_id": str(uuid.uuid4())}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    db = SessionLocal()
    try:
        response = pipeline.chat(
            user_message=request.message,
            session_id=request.session_id,
            db=db
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
