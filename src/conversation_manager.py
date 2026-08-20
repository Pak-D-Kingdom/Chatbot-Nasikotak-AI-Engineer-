import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import os
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
                "delivery_time": None,
                "fulfillment_method": None,
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
        # NOTE: field ini butuh `package_name` tersedia di MessageAnalysis (sales_engine.py).
        # Kalau atribut di sana namanya berbeda (mis. `product` atau `selected_product`),
        # sesuaikan nama atribut di baris getattr() di bawah ini.
        package_name = getattr(analysis, "package_name", None)
        if package_name is not None:
            session["selected_product"] = package_name

        # delivery_time & fulfillment_method: dibutuhkan untuk cek kelengkapan
        # data invoice di ALUR PEMESANAN (lihat prompt_templates.py). Tanpa ini,
        # bot akan terus menganggap data belum lengkap walau customer sudah
        # menjawabnya, karena tidak pernah diakumulasi ke session.
        delivery_time = getattr(analysis, "delivery_time", None)
        if delivery_time is not None:
            session["delivery_time"] = delivery_time

        fulfillment_method = getattr(analysis, "fulfillment_method", None)
        if fulfillment_method is not None:
            session["fulfillment_method"] = fulfillment_method
            
        # Update intent (Bisa naik atau turun, tapi biasanya purchase_intent kita jaga agar tidak mudah turun drastis)
        # Logika sederhana: jika intent baru lebih tinggi secara ordinal, kita update.
        intent_levels = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "READY_TO_ORDER": 3}
        current_level = intent_levels.get(session.get("purchase_intent", "LOW"), 0)
        
        normalized_pi = analysis.purchase_intent.upper() if analysis.purchase_intent else "LOW"
        new_level = intent_levels.get(normalized_pi, 0)
        
        # Contoh: hanya update kalau naik, ATAU kalau turun drastis karena komplain/batal
        # Untuk sekarang kita override saja untuk demonstrasi dinamis
        if normalized_pi in intent_levels:
             session["purchase_intent"] = normalized_pi
             
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
        
    def get_history(self, session_id: str, limit: int = 5, max_chars: int = 2000) -> List[Dict[str, str]]:
        """
        Mengambil sejumlah history terakhir untuk konteks LLM, dibatasi oleh jumlah pesan dan max_chars.
        """
        session = self.get_session(session_id)
        recent = session["messages"][-limit:]
        
        # Trim dari pesan terlama jika total chars melebihi max
        trimmed = []
        total = 0
        for msg in reversed(recent):
            msg_len = len(msg.get("text", ""))
            if total + msg_len > max_chars:
                break
            trimmed.append(msg)
            total += msg_len
        
        return list(reversed(trimmed))