import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from src.config import FAISS_INDEX_DIR, MAX_CONVERSATION_HISTORY, RAG_TOP_K, RAG_MAX_CONTEXT_TOKENS
from src.llm_service import LLMService
from src.rag_service import RAGService
from src.sales_engine import SalesEngine, MessageAnalysis
from src.conversation_manager import ConversationManager
from src.lead_manager import LeadManager
from src.database import get_db, init_db
from src.outlet_service import OutletService

class ChatPipeline:
    """
    Full end-to-end chatbot pipeline.
    Menggabungkan: RAG retrieval -> LLM -> Sales Engine -> Lead Management
    """

    def __init__(self):
        self.llm = LLMService()
        self.rag = RAGService(index_dir=FAISS_INDEX_DIR)
        self.rag.load_index()                  # Load FAISS index dari disk
        self.sales = SalesEngine()
        self.conv_manager = ConversationManager()
        self.lead_manager = LeadManager()
        self.outlet_service = OutletService()
    
    def chat(self, user_message: str, session_id: str = None, 
             db: Session = None) -> Dict[str, Any]:
        """
        Full pipeline:
        1. Load/create session
        2. RAG retrieval
        3. Build prompt (system + RAG context + history + message)
        4. Call LLM -> structured output
        5. Run sales engine (recommendation, price calc, upsell)
        6. Update session context
        7. Check lead trigger
        8. Return response
        """
        # --- 1. Session ---
        if session_id is None:
            session_id = str(uuid.uuid4())
        session = self.conv_manager.get_session(session_id)

        # --- 2. RAG Retrieval ---
        rag_results = self.rag.search(user_message, top_k=RAG_TOP_K)
        rag_context = self.rag.construct_context(rag_results, max_chars=RAG_MAX_CONTEXT_TOKENS)

        # --- 3+4. LLM Call with history ---
        history = self.conv_manager.get_history(session_id, 
                                                 limit=MAX_CONVERSATION_HISTORY)
        # Convert history format: {"sender":..., "text":...} -> {"role":..., "content":...}
        formatted_history = []
        for msg in history:
            role = "assistant" if msg.get("sender") == "bot" else "user"
            formatted_history.append({"role": role, "content": msg.get("text", "")})
        
        # Inject RAG context into collected entities for LLM awareness
        collected_entities = {
            "quantity": session.get("quantity"),
            "budget_per_box": session.get("budget_per_box"),
            "event_type": session.get("event_type"),
            "location": session.get("location"),
            "event_date": session.get("event_date"),
            "customer_name": session.get("customer_name"),
            "customer_phone": session.get("customer_phone"),
            "package_name": session.get("selected_product"),
            "delivery_method": session.get("delivery_method"),
        }

        # Prepend RAG context to user message for grounding
        augmented_message = user_message
        if rag_context:
            augmented_message = (
                f"[KONTEKS DARI KNOWLEDGE BASE]\n{rag_context}\n"
                f"[END KONTEKS]\n\n"
                f"Pesan customer: {user_message}"
            )

        llm_response = self.llm.chat_with_history(
            user_message=augmented_message,
            history=formatted_history,
            collected_entities=collected_entities,
            raw_user_message=user_message
        )

        # Jika LLMService gagal total (lihat chat_with_history's except block),
        # ia return {"error": "..."} tanpa key "reply". Tanpa penanganan ini,
        # customer akan menerima bubble kosong tanpa penjelasan apa pun.
        if "error" in llm_response and "reply" not in llm_response:
            print(f"[ERROR] chat_with_history gagal untuk session {session_id}: {llm_response['error']}")
            llm_response = {
                "reply": (
                    "Maaf kak, sistem kami sedang sedikit gangguan 🙏 "
                    "Boleh coba kirim ulang pesannya sebentar lagi?"
                ),
                "intent": "other",
                "purchase_intent": "low",
                "entities": {},
                "actions": [],
                "needs_handover": False,
                "handover_reason": None,
            }

        # --- 5. Sales Engine: enrich response ---
        # Parse entities from LLM response to update session
        entities = llm_response.get("entities", {})
        analysis = MessageAnalysis(
            intent=llm_response.get("intent", "other"),
            purchase_intent=(llm_response.get("purchase_intent") or "LOW").upper(),
            budget=entities.get("budget_per_box"),
            quantity=entities.get("quantity"),
            event_type=entities.get("event_type"),
            location=entities.get("location"),
            event_date=entities.get("event_date"),
            package_name=entities.get("package_name"),
            delivery_method=entities.get("delivery_method"),
        )
        
        # --- 5.5. Pickup Business Logic ---
        delivery_method = entities.get("delivery_method") or session.get("delivery_method")
        location = entities.get("location") or session.get("location")
        quantity = entities.get("quantity") or session.get("quantity")

        # Auto-set pickup jika qty < 25
        if quantity and quantity < 25 and delivery_method != "pickup":
            delivery_method = "pickup"
            analysis.delivery_method = "pickup"

        # Cek jarak ke outlet terdekat jika ada lokasi
        if location:
            nearest = self.outlet_service.find_nearest_by_address(location, limit=3)
            if nearest:
                min_distance = nearest[0]["distance_km"]
                is_address_question = self._is_outlet_address_inquiry(user_message, history=history)

                if is_address_question or delivery_method == "pickup":
                    # Tampilkan HANYA jika user menanyakan alamat outlet ATAU pesanan wajib pickup (< 25 box)
                    outlets_to_show = nearest[:1]
                    include_cost = (delivery_method == "pickup" and not is_address_question)
                    outlet_info = self.outlet_service.format_outlet_info(outlets_to_show, include_cost=include_cost)
                    
                    base_reply = llm_response.get("reply", "").rstrip()
                    # Bersihkan jika LLM menyebut kalimat template 'otomatis ditampilkan oleh sistem'
                    import re
                    base_reply = re.sub(
                        r"(?i)\s*[^.\n]*(?:otomatis ditampilkan|ditampilkan secara otomatis|ditampilkan oleh sistem)[^.\n]*[\.\!]?",
                        "",
                        base_reply
                    ).rstrip()
                    
                    if re.search(r"(?i)outlet terdekat[^\n]*:\s*$", base_reply):
                        llm_response["reply"] = f"{base_reply}\n\n{outlet_info}"
                    else:
                        llm_response["reply"] = (
                            f"{base_reply}\n\n"
                            f"📍 Outlet Terdekat:\n{outlet_info}"
                        )
                elif min_distance > 3.0 and not llm_response.get("needs_handover"):
                    # Jarak > 3 km untuk delivery catering: handover ongkir
                    # Cegah handover jika respons berkaitan dengan menu dine-in / website
                    reply_lower = (llm_response.get("reply") or "").lower()
                    is_dinein_or_website = any(k in reply_lower for k in [
                        "dine-in", "dine in", "makan di tempat", "hanya tersedia di outlet",
                        "hanya bisa dipesan melalui website", "melalui website kami"
                    ])

                    if not is_dinein_or_website:
                        llm_response["needs_handover"] = True
                        llm_response["handover_reason"] = f"Jarak pengiriman > 3 km ({min_distance} km), perlu diskusi ongkir."
                        
                        admin = self.llm._get_next_markom_admin()
                        admin_phone = admin['phone']
                        if admin_phone.startswith("0"):
                            admin_phone = "62" + admin_phone[1:]
                        elif admin_phone.startswith("+"):
                            admin_phone = admin_phone[1:]
                        
                        from urllib.parse import quote
                        message = f"Halo Admin, saya ingin diskusi mengenai ongkir pesanan catering ke {location}."
                        wa_link = f"https://api.whatsapp.com/send?phone={admin_phone}&text={quote(message)}"
                        
                        llm_response["assigned_admin"] = admin["name"]
                        llm_response["handover_link"] = wa_link
                        if "handover_admin" not in llm_response.get("actions", []):
                            llm_response.setdefault("actions", []).append("handover_admin")
                            
                        base_reply = llm_response.get("reply", "").rstrip()
                        llm_response["reply"] = (
                            f"{base_reply}\n\nLokasi pengiriman berjarak {min_distance} km dari outlet terdekat. "
                            f"Untuk hal ini, saya hubungkan ke admin kami untuk diskusi ongkir ya kak 🙏\n"
                            f"{admin['name']}: {wa_link}"
                        )


        # --- 6. Update session context ---
        updated_session = self.conv_manager.update_session(session_id, analysis)

        # --- 6.5 Invoice Generation ---
        if "generate_invoice" in llm_response.get("actions", []):
            pkg_name = updated_session.get("selected_product")
            qty = updated_session.get("quantity")
            if pkg_name and qty:
                products = self.sales.get_all_products(db)
                product = next((p for p in products if pkg_name.lower() in p.name.lower()), None)
                if product:
                    try:
                        price_info = self.sales.calculate_price(db, product, qty)
                        total_price = price_info.get("final_total", 0)
                    except ValueError:
                        # Fallback if quantity < minimum_order (should not happen if LLM did its job, but just in case)
                        total_price = product.price * qty
                        
                    final_price = product.price # harga satuan
                    
                    ongkir = 0
                    if delivery_method == "pickup":
                        if 'nearest' in locals() and nearest:
                            ongkir = nearest[0].get("pickup_cost", 0)
                            outlet_name = nearest[0].get("name", "Outlet")
                            deliv_str = f"Pickup di {outlet_name}"
                        else:
                            ongkir = 0
                            deliv_str = f"Pickup di outlet terdekat (Menunggu konfirmasi)"
                    else:
                        deliv_str = f"Delivery ke {updated_session.get('location', '-')}"
                    
                    grand_total = total_price + ongkir
                    ongkir_str = f"Rp{ongkir:,.0f}" if ongkir > 0 else "Konfirmasi Admin" if delivery_method != "pickup" else "GRATIS"
                    
                    invoice_text = (
                        f"📝 **Ringkasan Pesanan**\n"
                        f"• Paket: {product.name}\n"
                        f"• Harga Satuan: Rp{final_price:,.0f}\n"
                        f"• Jumlah: {qty} box\n"
                        f"• Subtotal: Rp{total_price:,.0f}\n"
                        f"• Metode: {deliv_str}\n"
                        f"• Ongkir: {ongkir_str}\n"
                        f"• **TOTAL ESTIMASI: Rp{grand_total:,.0f}**\n\n"
                        f"Pesanan kakak sudah siap! Silakan klik tombol di bawah ini untuk mengirim pesanan ke Admin kami melalui WhatsApp ya kak 👇"
                    )
                    
                    updated_session["invoice_text"] = invoice_text
                    updated_session["purchase_intent"] = "READY_TO_ORDER"
                    
                    base_reply = llm_response.get("reply", "").rstrip()
                    llm_response["reply"] = f"{base_reply}\n\n{invoice_text}"

        # Save messages to memory (and optionally DB)
        if db:
            self.conv_manager.add_message(db, session_id, "user", user_message,
                                           intent=analysis.intent, 
                                           purchase_intent=analysis.purchase_intent)
            self.conv_manager.add_message(db, session_id, "bot", 
                                           llm_response.get("reply", ""),
                                           intent=analysis.intent,
                                           purchase_intent=analysis.purchase_intent)
        else:
            # In-memory only
            session["messages"].append({"sender": "user", "text": user_message})
            session["messages"].append({"sender": "bot", "text": llm_response.get("reply", "")})

        # --- 7. Lead trigger ---
        lead_saved = None
        whatsapp_link = None
        current_intent = updated_session.get("purchase_intent", "LOW")
        if self.lead_manager.should_capture_lead(current_intent) and db:
            lead_saved = self.lead_manager.save_lead(db, updated_session)
            # Generate WhatsApp link if admin assigned
            assigned_admin = llm_response.get("assigned_admin")
            if not assigned_admin:
                admin = self.llm._get_next_markom_admin()
                admin_phone = admin["phone"]
            else:
                # Find phone from admin name
                from src.config import MARKOM_ADMINS
                admin_phone = next(
                    (a["phone"] for a in MARKOM_ADMINS if a["name"] == assigned_admin),
                    MARKOM_ADMINS[0]["phone"]
                )
            whatsapp_link = self.lead_manager.generate_whatsapp_link(
                admin_phone, updated_session
            )

        # --- 8. Build final response ---
        result = {
            "session_id": session_id,
            "reply": llm_response.get("reply", ""),
            "intent": llm_response.get("intent", "other"),
            "purchase_intent": current_intent,
            "entities": dict(updated_session),
            "actions": llm_response.get("actions", []),
            "needs_handover": llm_response.get("needs_handover", False),
            "handover_reason": llm_response.get("handover_reason"),
            "rag_sources": [doc.metadata.get("source", "") for doc in rag_results],
        }

        if lead_saved:
            result["lead_id"] = lead_saved.id
            result["lead_status"] = "captured"
        if whatsapp_link:
            result["whatsapp_link"] = whatsapp_link

        return result

    def _is_outlet_address_inquiry(self, user_message: str, history: List[Dict[str, Any]] = None) -> bool:
        """
        Deteksi apakah user sedang menanyakan alamat/lokasi outlet terdekat.
        HANYA True jika user secara spesifik menanyakan alamat/lokasi/outlet terdekat,
        atau user sedang merespons pertanyaan bot sebelumnya mengenai daerah/lokasi outlet.
        """
        msg = user_message.lower()

        # 1. Kata kunci langsung mengenai alamat atau cabang/outlet terdekat
        address_keywords = [
            "alamat", "almt", "lokasi", "tempat", "posisi",
            "outlet terdekat", "outlet terdekt", "cabang terdekat", "paling dekat",
            "ada cabang", "ada outlet", "cabang di", "outlet di"
        ]
        if any(kw in msg for kw in address_keywords):
            return True

        # 2. Pertanyaan "di mana" / "dimana" / "mana" terkait outlet / cabang / warung / makan / beli
        if any(w in msg for w in ["dimana", "di mana", "ke mana", "kemana", "mana"]):
            if any(target in msg for target in ["outlet", "otlet", "cabang", "warung", "resto", "pak d", "makan", "beli", "lokasi", "tempat"]):
                return True

        # 3. Kata "terdekat" jika didampingi konteks mencari outlet/makan
        if any(w in msg for w in ["terdekat", "terdekt"]) and any(t in msg for t in ["outlet", "otlet", "cabang", "paket", "menu", "pak d", "makan"]):
            return True

        # 4. Cek riwayat pesan: jika pesan bot terakhir menanyakan lokasi/daerah untuk mencari outlet terdekat
        if history:
            last_bot_msg = None
            for item in reversed(history):
                sender = item.get("sender") or item.get("role")
                if sender in ["bot", "assistant"]:
                    last_bot_msg = (item.get("text") or item.get("content") or "").lower()
                    break
            
            if last_bot_msg:
                # Bot sebelumnya menanyakan daerah/lokasi untuk mencari outlet terdekat
                if any(w in last_bot_msg for w in ["outlet", "cabang"]) and any(q in last_bot_msg for q in ["daerah", "lokasi", "mana"]):
                    return True

        return False