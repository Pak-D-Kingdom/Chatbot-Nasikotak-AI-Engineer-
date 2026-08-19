from urllib.parse import quote
from sqlalchemy.orm import Session
from src.database import Lead
from src.config import ORDER_WEB_URL

class LeadManager:

    def should_capture_lead(self, purchase_intent: str) -> bool:
        """Cek apakah purchase intent sudah cukup tinggi untuk capture lead."""
        return purchase_intent.upper() in ("HIGH", "READY_TO_ORDER")

    def save_lead(self, db: Session, session_context: dict) -> Lead:
        """
        Menyimpan lead dari session context ke database.
        Params:
            db: SQLAlchemy session
            session_context: dict dari ConversationManager.get_session()
                Keys: quantity, budget_per_box, event_type, event_date, 
                      location, selected_product, customer_name, 
                      customer_phone, purchase_intent
        Returns:
            Lead object yang baru disimpan
        """
        lead = Lead(
            name=session_context.get("customer_name"),
            phone=session_context.get("customer_phone"),
            quantity=session_context.get("quantity"),
            budget=session_context.get("budget_per_box"),
            event_type=session_context.get("event_type"),
            event_date=session_context.get("event_date"),
            location=session_context.get("location"),
            product_id=session_context.get("selected_product"),
            purchase_intent=session_context.get("purchase_intent"),
            status="new",
            notes=self._generate_notes(session_context),
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    def _generate_notes(self, ctx: dict) -> str:
        """Auto-generate ringkasan lead dari session context."""
        parts = []
        if ctx.get("event_type"):
            parts.append(f"Acara: {ctx['event_type']}")
        if ctx.get("quantity"):
            parts.append(f"Qty: {ctx['quantity']} box")
        if ctx.get("budget_per_box"):
            parts.append(f"Budget: Rp{ctx['budget_per_box']:,.0f}/box")
        if ctx.get("location"):
            parts.append(f"Lokasi: {ctx['location']}")
        if ctx.get("event_date"):
            parts.append(f"Tanggal: {ctx['event_date']}")
        return " | ".join(parts) if parts else "Lead dari chatbot"

    def generate_whatsapp_link(self, admin_phone: str, session_context: dict, 
                                product_name: str = None) -> str:
        """
        Generate WhatsApp CTA link dengan pre-filled message.
        Format: https://wa.me/{phone}?text={encoded_message}
        """
        qty = session_context.get("quantity", "-")
        event = session_context.get("event_type", "-")
        date = session_context.get("event_date", "-")
        location = session_context.get("location", "-")
        budget = session_context.get("budget_per_box")
        name = session_context.get("customer_name", "")

        budget_str = f"Rp{budget:,.0f}/box" if budget else "-"
        product_str = product_name or session_context.get("selected_product", "-")

        message = (
            f"Halo Admin, saya ingin memesan nasi kotak:\n"
            f"Paket: {product_str}\n"
            f"Jumlah: {qty} box\n"
            f"Acara: {event}\n"
            f"Tanggal: {date}\n"
            f"Lokasi: {location}\n"
            f"Budget: {budget_str}\n"
        )
        if name:
            message += f"Nama: {name}\n"

        return f"https://wa.me/{admin_phone}?text={quote(message)}"

    def generate_order_web_link(self, session_context: dict) -> str:
        """Generate link ke halaman web pemesanan."""
        return ORDER_WEB_URL

    def get_all_leads(self, db: Session) -> list:
        """Ambil semua leads dari database."""
        return db.query(Lead).order_by(Lead.created_at.desc()).all()

    def get_leads_by_status(self, db: Session, status: str = "new") -> list:
        """Ambil leads berdasarkan status."""
        return db.query(Lead).filter(Lead.status == status).all()
