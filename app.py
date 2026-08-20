import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Cookie, Depends, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.pipeline import ChatPipeline
from src.database import SessionLocal, init_db, UserForm

# Initialize database
init_db()

# Initialize FastAPI app
app = FastAPI(title="AI Sales Chatbot API")

# Initialize ChatPipeline
pipeline = ChatPipeline()

# Ensure static directory exists
import os
os.makedirs("static", exist_ok=True)

# Mount static and image files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/image", StaticFiles(directory="image"), name="image")

# Models
class SessionCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str

class ChatRequest(BaseModel):
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

@app.get("/api/session")
async def get_session(x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    nasikotak_session = x_session_id
    if not nasikotak_session:
        return {"authenticated": False}
        
    db = SessionLocal()
    try:
        user_form = db.query(UserForm).filter(UserForm.session_id == nasikotak_session).first()
        if user_form:
            return {
                "authenticated": True,
                "user": {
                    "id": user_form.id,
                    "name": user_form.name,
                    "phone": user_form.phone
                }
            }
    finally:
        db.close()
        
    return {"authenticated": False}

@app.post("/api/session/new")
async def new_session(request: SessionCreateRequest, response: Response):
    db = SessionLocal()
    try:
        # Check if phone already exists
        existing_user = db.query(UserForm).filter(UserForm.phone == request.customer_phone).first()
        
        if existing_user:
            session_id = existing_user.session_id
            session = pipeline.conv_manager.get_session(session_id)
            session["customer_name"] = existing_user.name
            session["customer_phone"] = existing_user.phone
        else:
            session_id = str(uuid.uuid4())
            session = pipeline.conv_manager.get_session(session_id)
            session["customer_name"] = request.customer_name
            session["customer_phone"] = request.customer_phone
            
            new_form = UserForm(
                session_id=session_id,
                name=request.customer_name,
                phone=request.customer_phone
            )
            db.add(new_form)
            db.commit()
            
        # Removed cookie setting, session_id will be stored in sessionStorage by frontend
        
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        print(f"Error saving user form: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()

@app.post("/api/logout")
async def logout(response: Response):
    response.delete_cookie(key="nasikotak_session", httponly=True, samesite="lax")
    return {"authenticated": False}

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, x_session_id: Optional[str] = Header(None, alias="X-Session-ID")):
    nasikotak_session = x_session_id
    if not nasikotak_session:
        raise HTTPException(status_code=401, detail="Unauthorized. Please submit the form first.")
        
    db = SessionLocal()
    try:
        response = pipeline.chat(
            user_message=request.message,
            session_id=nasikotak_session,
            db=db
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/outlets")
async def get_outlets():
    """Return daftar semua outlet aktif."""
    return pipeline.outlet_service.get_active_outlets()

@app.get("/api/outlets/nearest")
async def get_nearest_outlets(address: str, limit: int = 3):
    """Cari outlet terdekat dari alamat."""
    result = pipeline.outlet_service.find_nearest_by_address(address, limit)
    if result is None:
        raise HTTPException(status_code=400, detail="Gagal geocode alamat")
    return result

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
