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

        user_msg_lower = (user_message or "").lower()
        reservation_keywords = [
            "reservasi", "booking", "pesan meja", "booking meja", 
            "makan di tempat", "dine in", "dine-in", "makan di outlet", 
            "meja untuk", "makan disana", "makan di sana"
        ]
        is_reservation_chat = (
            bool(session.get("is_reservation", False)) or
            any(k in user_msg_lower for k in reservation_keywords) or
            bool(session.get("reservation_time")) or
            bool(session.get("total_people"))
        )
        if is_reservation_chat:
            session["is_reservation"] = True

        # --- 2. RAG Retrieval ---
        # Jika dalam alur reservasi dan menanyakan menu, utamakan pencarian menu ayam bakar dine-in outlet
        is_asking_menu = any(w in user_msg_lower for w in [
            "menu", "makan", "paket", "harga", "ayam", "rekomendasi", "pilihan", "tersedia", "ada apa", "apa saja"
        ])
        if is_reservation_chat and is_asking_menu:
            rag_query = f"menu ayam bakar paket komplit paket keluarga dahsyat dine in outlet makan di tempat {user_message}"
        else:
            rag_query = user_message

        rag_results = self.rag.search(rag_query, top_k=RAG_TOP_K)
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
            "reservation_time": session.get("reservation_time"),
            "total_people": session.get("total_people"),
            "is_reservation": is_reservation_chat,
        }

        # Prepend RAG context to user message for grounding
        reservation_note = ""
        if is_reservation_chat:
            reservation_note = (
                "[KONTEKS KHUSUS: ALUR RESERVASI TEMPAT / MEJA (DINE-IN)]\n"
                "Customer sedang dalam proses RESERVASI MEJA untuk makan di outlet Ayam Bakar Pak D.\n"
                "Jika customer menanyakan menu/makanan: Sajikan MENU AYAM BAKAR DINE-IN OUTLET (Paket Komplit, Paket Keluarga/Dahsyat/Family, olahan Ayam Bakar khas Pak D), BUKAN nasi kotak katering dan JANGAN sebut syarat minimum 20 box.\n\n"
            )

        augmented_message = user_message
        if rag_context:
            augmented_message = (
                f"{reservation_note}"
                f"[KONTEKS DARI KNOWLEDGE BASE]\n{rag_context}\n"
                f"[END KONTEKS]\n\n"
                f"Pesan customer: {user_message}"
            )
        elif reservation_note:
            augmented_message = f"{reservation_note}Pesan customer: {user_message}"

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
            reservation_time=entities.get("reservation_time"),
            total_people=entities.get("total_people"),
            customer_name=entities.get("customer_name"),
            customer_phone=entities.get("customer_phone"),
        )
        
        # --- 5.5. Outlet Location & Business Logic ---
        delivery_method = entities.get("delivery_method") or session.get("delivery_method")
        location = entities.get("location") or session.get("location")
        quantity = entities.get("quantity") or session.get("quantity")
        is_reservation = (
            is_reservation_chat or
            session.get("is_reservation", False) or
            "generate_reservation" in llm_response.get("actions", []) or 
            llm_response.get("intent") == "reservation" or 
            analysis.intent == "reservation"
        )
        if is_reservation:
            session["is_reservation"] = True
            analysis.is_reservation = True

        is_outlet_inquiry = any(k in user_msg_lower for k in [
            "cabang", "outlet", "lokasi", "terdekat", "dimana", "di mana", "alamat"
        ])

        # Auto-set pickup jika qty < 25 (khusus catering)
        if not is_reservation and quantity and quantity < 25 and delivery_method != "pickup":
            delivery_method = "pickup"
            analysis.delivery_method = "pickup"

        # Cek apakah user memilih cabang dari rekomendasi sebelumnya (misal "nomor 1", "yang Rungkut", dsb)
        candidate_outlets = session.get("candidate_outlets")
        matched_outlet = self.outlet_service.match_outlet_from_input(user_message, candidate_outlets)
        if matched_outlet:
            location = matched_outlet["name"]
            analysis.location = matched_outlet["name"]
            entities["location"] = matched_outlet["name"]
            session["location"] = matched_outlet["name"]
            session["pickup_outlet"] = matched_outlet["name"]

        # Cek outlet terdekat jika ada lokasi/alamat tujuan
        if location:
            nearest = self.outlet_service.find_nearest_by_address(location, limit=5)
            if nearest:
                session["candidate_outlets"] = nearest
                min_distance = nearest[0]["distance_km"]
                # Cek apakah user sudah memilih cabang spesifik (misal: "Pak D - Rungkut 2" atau "Rungkut 2")
                exact_outlet_chosen = any(
                    o["name"].lower() in location.lower() or 
                    o["name"].replace("Pak D - ", "").strip().lower() in location.lower()
                    for o in self.outlet_service.outlets
                )

                is_address_question = self._is_outlet_address_inquiry(user_message, history=history)

                # Kasus 1: Delivery Katering dengan jarak > 3 km -> Handover admin diskusi ongkir
                reply_lower = (llm_response.get("reply") or "").lower()
                is_dinein_or_website = any(k in reply_lower for k in [
                    "dine-in", "dine in", "makan di tempat", "hanya tersedia di outlet",
                    "hanya bisa dipesan melalui website", "melalui website kami"
                ])
                if delivery_method == "delivery" and min_distance > 3.0 and not is_reservation and not is_dinein_or_website and not llm_response.get("needs_handover"):
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
                # Kasus 2: Tanya cabang, pickup, atau reservasi meja di mana user memberikan alamat tujuan tapi belum memilih 1 cabang spesifik
                elif not exact_outlet_chosen and (delivery_method == "pickup" or is_reservation or is_outlet_inquiry or is_address_question or entities.get("location")):
                    llm_response["suggested_outlets"] = [
                        {"name": o["name"], "distance_km": o["distance_km"]} for o in nearest
                    ]
                    include_cost = (delivery_method == "pickup" and not is_reservation and not is_address_question)
                    outlet_info = self.outlet_service.format_outlet_info(
                        nearest, 
                        include_cost=include_cost
                    )
                    base_reply = llm_response.get("reply", "").rstrip()
                    # Bersihkan jika LLM menyebut kalimat template 'otomatis ditampilkan oleh sistem'
                    import re
                    base_reply = re.sub(
                        r"(?i)\s*[^.\n]*(?:otomatis ditampilkan|ditampilkan secara otomatis|ditampilkan oleh sistem)[^.\n]*[\.\!]?",
                        "",
                        base_reply
                    ).rstrip()
                    # Hanya append jika daftar outlet belum ada di reply LLM
                    if "📍 Pak D -" not in base_reply and "1. 📍" not in base_reply:
                        if is_reservation:
                            llm_response["reply"] = (
                                f"{base_reply}\n\n"
                                f"📍 **5 Outlet Ayam Bakar Pak D Terdekat dari lokasi tujuan ({location}):**\n"
                                f"{outlet_info}\n\n"
                                f"Dari 5 pilihan cabang di atas, cabang mana yang ingin kakak pilih untuk reservasi?"
                            )
                        else:
                            llm_response["reply"] = (
                                f"{base_reply}\n\n"
                                f"📍 **Outlet Terdekat dari lokasi ({location}):**\n"
                                f"{outlet_info}"
                            )

        # Validasi jam operasional untuk reservasi meja (10:00 - 21:30 WIB)
        if is_reservation:
            raw_res_time = entities.get("reservation_time") or session.get("reservation_time")
            if raw_res_time:
                is_valid_time, time_warn = self.outlet_service.validate_reservation_time(raw_res_time)
                if not is_valid_time:
                    analysis.reservation_time = None
                    entities["reservation_time"] = None
                    session["reservation_time"] = None
                    base_reply = llm_response.get("reply", "").rstrip()
                    llm_response["reply"] = f"{base_reply}\n\n⚠️ {time_warn} Boleh dibantu sesuaikan jam kedatangannya ya kak 🙏"


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

        # --- 6.6 Reservation Generation ---
        is_reservation = (
            session.get("is_reservation", False) or
            "generate_reservation" in llm_response.get("actions", []) or 
            llm_response.get("intent") == "reservation" or 
            analysis.intent == "reservation"
        )
        if is_reservation:
            res_date = updated_session.get("event_date")
            res_time = updated_session.get("reservation_time")
            res_people = updated_session.get("total_people")
            res_name = updated_session.get("customer_name")
            res_outlet = updated_session.get("location")
            menu_pilihan = updated_session.get("selected_product")
            
            # Cek apakah cabang sudah dipilih secara spesifik dari daftar outlet
            chosen_outlet_obj = None
            if res_outlet:
                chosen_outlet_obj = self.outlet_service.match_outlet_from_input(res_outlet)
            
            # Ringkasan HANYA dibuat jika data reservasi LENGKAP:
            # 1. Nama pemesan ada
            # 2. Tanggal ada
            # 3. Jam ada
            # 4. Jumlah orang ada
            # 5. Cabang outlet spesifik sudah dipilih (bukan masih bertanya alamat tujuan/opsi)
            if res_date and res_time and res_people and res_name and chosen_outlet_obj:
                outlet_name = chosen_outlet_obj["name"]
                menu_line = f"• Pilihan Menu: {menu_pilihan}\n" if menu_pilihan else ""
                reservation_text = (
                    f"📋 **Ringkasan Reservasi Tempat**\n"
                    f"• Nama: {res_name}\n"
                    f"• Tanggal: {res_date}\n"
                    f"• Jam: {res_time}\n"
                    f"• Jumlah: {res_people} orang\n"
                    f"• Cabang Outlet: {outlet_name}\n"
                    f"{menu_line}\n"
                    f"Data reservasi kakak sudah kami siapkan! Silakan klik tombol di bawah ini untuk konfirmasi langsung ke Admin WhatsApp kami ya kak 👇"
                )

                
                updated_session["reservation_text"] = reservation_text
                updated_session["purchase_intent"] = "READY_TO_ORDER"
                
                base_reply = llm_response.get("reply", "").rstrip()
                if "Ringkasan Reservasi" not in base_reply:
                    llm_response["reply"] = f"{base_reply}\n\n{reservation_text}"

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
        if self.lead_manager.should_capture_lead(current_intent):
            if db:
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
        # Hanya sertakan whatsapp_link ke frontend jika:
        # 1. Terjadi handover admin (handover_link)
        # 2. Ringkasan invoice pesanan catering sudah lengkap (invoice_text)
        # 3. Ringkasan reservasi meja sudah lengkap (reservation_text)
        show_wa_button = False
        if llm_response.get("needs_handover") and llm_response.get("handover_link"):
            whatsapp_link = llm_response.get("handover_link")
            show_wa_button = True
        elif "invoice_text" in updated_session or "reservation_text" in updated_session:
            show_wa_button = True

        if show_wa_button and not whatsapp_link:
            admin = self.llm._get_next_markom_admin()
            admin_phone = admin["phone"]
            whatsapp_link = self.lead_manager.generate_whatsapp_link(
                admin_phone, updated_session
            )

        if show_wa_button and whatsapp_link:
            result["whatsapp_link"] = whatsapp_link
        if "suggested_outlets" in llm_response:
            result["suggested_outlets"] = llm_response["suggested_outlets"]

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