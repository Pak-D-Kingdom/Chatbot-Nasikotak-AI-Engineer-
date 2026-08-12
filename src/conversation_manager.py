import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.database import Conversation
from src.sales_engine import MessageAnalysis

class ConversationManager:
    def __init__(self):
        # In-memory session store (Ideally ini disimpan di Redis/DB untuk production)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
    def get_session(self, session_id: str) -> Dict[str, Any]:
        """
        Mengambil atau membuat session baru.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "session_id": session_id,
                "quantity": None,
                "budget_per_box": None,
                "event_type": None,
                "location": None,
                "event_date": None,
                "selected_product": None,
                "customer_name": None,
                "customer_phone": None,
                "purchase_intent": "LOW",
                "messages": []
            }
        return self.sessions[session_id]

    def update_session(self, session_id: str, analysis: MessageAnalysis) -> Dict[str, Any]:
        """
        Mengakumulasi entitas yang diekstrak oleh SalesEngine ke dalam session state.
        Hanya mengupdate jika nilai baru tidak null.
        """
        session = self.get_session(session_id)
        
        # Accumulate entities
        if analysis.budget is not None:
            session["budget_per_box"] = analysis.budget
        if analysis.quantity is not None:
            session["quantity"] = analysis.quantity
        if analysis.event_type is not None:
            session["event_type"] = analysis.event_type
        if analysis.location is not None:
            session["location"] = analysis.location
        if analysis.event_date is not None:
            session["event_date"] = analysis.event_date
            
        # Update intent (Bisa naik atau turun, tapi biasanya purchase_intent kita jaga agar tidak mudah turun drastis)
        # Logika sederhana: jika intent baru lebih tinggi secara ordinal, kita update.
        intent_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "READY_TO_ORDER": 3}
        current_level = intent_levels.get(session.get("purchase_intent", "LOW"), 0)
        new_level = intent_levels.get(analysis.purchase_intent, 0)
        
        # Contoh: hanya update kalau naik, ATAU kalau turun drastis karena komplain/batal
        # Untuk sekarang kita override saja untuk demonstrasi dinamis
        if analysis.purchase_intent in intent_levels:
             session["purchase_intent"] = analysis.purchase_intent
             
        return session
        
    def add_message(self, db: Session, session_id: str, sender: str, message: str, intent: str = None, purchase_intent: str = None):
        """
        Menambahkan history chat ke memori dan menyimpan persistensinya ke SQLite.
        """
        session = self.get_session(session_id)
        
        # Add to memory
        msg_obj = {"sender": sender, "text": message}
        session["messages"].append(msg_obj)
        
        # Simpan ke DB SQLite `conversations` table
        db_message = Conversation(
            session_id=session_id,
            sender=sender,
            message=message,
            intent=intent,
            purchase_intent=purchase_intent
        )
        db.add(db_message)
        db.commit()
        
    def get_history(self, session_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Mengambil sejumlah history terakhir untuk konteks LLM.
        """
        session = self.get_session(session_id)
        return session["messages"][-limit:]
