import json
import re
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from groq import Groq

from src.config import (
    GROQ_API_KEY, 
    LLM_MODEL, 
    LLM_MAX_TOKENS, 
    LLM_TEMPERATURE, 
    LLM_MAX_RETRIES,
    KNOWLEDGE_BASE_DIR,
    ORDER_WEB_URL,
    MARKOM_ADMINS
)
from src.prompt_templates import (
    build_system_prompt, 
    VALID_INTENTS, 
    ANCHOR_RULES, 
    JSON_FORMAT_INSTRUCTION
)

class Entity(BaseModel):
    """Extracted entities dari customer message"""
    quantity: Optional[int] = None
    budget_per_box: Optional[float] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None

class GeminiStructuredResponse(BaseModel):
    """Structured response schema untuk LLM (awalnya Gemini, sekarang Groq)"""
    reply: str
    intent: str
    purchase_intent: str
    entities: Entity
    actions: List[str]
    needs_handover: bool = False
    handover_reason: Optional[str] = None

def extract_json(response_text: str) -> Optional[dict]:
    """Ekstrak JSON dari teks respons, coba beberapa pattern"""
    json_patterns = [
        r'\{[\s\S]*\}',                          # broad pattern
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',      # nested pattern
    ]
    for pattern in json_patterns:
        match = re.search(pattern, response_text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
    return None

def clean_markdown(text: str) -> str:
    """Remove markdown formatting"""
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("##", "")
    text = text.replace("- ", "")
    return text

def check_handover_override(user_message: str, collected_entities: dict) -> Optional[str]:
    """
    Safety-net berbasis keyword/angka: dipakai kalau model TIDAK menandai needs_handover
    padahal pesan customer sebenarnya masuk kategori yang wajib di-handover.
    Return: reason (str) kalau perlu override, None kalau tidak.
    """
    text = user_message.lower()

    # 1. Pesanan sangat besar (>200 box)
    qty = collected_entities.get("quantity")
    if isinstance(qty, (int, float)) and qty > 200:
        return "Pesanan sangat besar (>200 box)"

    # 2. Custom menu / dietary kompleks di luar contoh standar KB
    dietary_hard_keywords = ["kontaminasi", "vegan strict", "alergi berat", "alergi parah"]
    if any(k in text for k in dietary_hard_keywords):
        return "Custom menu/dietary kompleks di luar standar KB"
    if "alergi" in text and any(k in text for k in ["jamin", "pastikan", "dijamin", "benar-benar"]):
        return "Custom menu/dietary kompleks di luar standar KB"

    # 3. Perubahan syarat pembayaran di luar standar (DP 50%)
    payment_keywords = ["termin", "cicil", "nyusul", "bayar setelah acara", "lunas setelah acara"]
    if any(k in text for k in payment_keywords):
        return "Permintaan syarat pembayaran di luar standar (DP 50%)"
    dp_match = re.search(r'dp\s*(\d+)\s*%', text)
    if dp_match and int(dp_match.group(1)) < 50:
        return "Permintaan DP di bawah standar 50%"

    # 4. Komplain terhadap pesanan yang sudah berjalan
    complaint_keywords = ["komplain", "keluhan", "kecewa", "telat", "terlambat", "basi", "rusak",
                           "kurang box", "salah kirim", "tidak sesuai pesanan"]
    if any(k in text for k in complaint_keywords):
        return "Komplain terhadap pesanan yang sudah berjalan"

    return None

class LLMService:
    """Centralized LLM client menggunakan Groq SDK."""
    
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY tidak ditemukan di config")
        self.client = Groq(api_key=GROQ_API_KEY)
        self.system_prompt = build_system_prompt(KNOWLEDGE_BASE_DIR)
        self._markom_round_robin_counter = {"index": 0}

    def _get_next_markom_admin(self):
        """Pilih admin Markom berikutnya secara round-robin"""
        idx = self._markom_round_robin_counter["index"] % len(MARKOM_ADMINS)
        admin = MARKOM_ADMINS[idx]
        self._markom_round_robin_counter["index"] += 1
        return admin

    def simple_chat(self, user_message: str) -> str:
        """Chat sederhana, return plain text response."""
        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=300
        )
        response_text = response.choices[0].message.content.strip()
        return clean_markdown(response_text)

    def chat_structured(self, user_message: str) -> dict:
        """Chat dengan structured JSON output, divalidasi Pydantic."""
        
        json_format_broad = """{
  "reply": "response in Indonesian",
  "intent": "pilih TEPAT SATU nilai saja dari: product_inquiry, price_inquiry, recommendation, ordering, other (JANGAN gabungkan dengan tanda | atau koma)",
  "purchase_intent": "pilih TEPAT SATU nilai saja dari: low, medium, high, ready_to_order",
  "entities": {
    "quantity": null or number,
    "budget_per_box": null or number,
    "event_type": null or string,
    "location": null or string,
    "event_date": null or string,
    "customer_name": null or string,
    "customer_phone": null or string
  },
  "actions": ["array berisi STRING singkat saja, contoh: [\\"show_products\\", \\"ask_quantity\\", \\"redirect_to_web\\"], JANGAN berupa object/dict, boleh kosong []"],
  "needs_handover": false,
  "handover_reason": null
}"""

        try:
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": f"{user_message}\n\nRespond ONLY as valid JSON in this format:\n{json_format_broad}"}
                        ],
                        max_tokens=LLM_MAX_TOKENS,
                        temperature=LLM_TEMPERATURE
                    )
                    break
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait_time = 2 ** attempt
                        print(f"[INFO] Rate limit tercapai, menunggu {wait_time}s sebelum coba lagi... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")
                        time.sleep(wait_time)
                        if attempt == LLM_MAX_RETRIES - 1:
                            raise
                    else:
                        raise

            response_text = response.choices[0].message.content.strip()
            response_json = extract_json(response_text)

            if response_json is None:
                return {
                    "reply": response_text[:200],
                    "intent": "other",
                    "purchase_intent": "low",
                    "entities": {},
                    "actions": [],
                    "error": "Could not parse JSON"
                }

            # Bersihkan intent
            raw_intent = str(response_json.get("intent", "other"))
            if raw_intent not in VALID_INTENTS:
                first_candidate = re.split(r'[|,]', raw_intent)[0].strip()
                response_json["intent"] = first_candidate if first_candidate in VALID_INTENTS else "other"

            # Bersihkan actions
            raw_actions = response_json.get("actions", [])
            if isinstance(raw_actions, list):
                cleaned_actions = []
                for a in raw_actions:
                    if isinstance(a, str):
                        cleaned_actions.append(a)
                    elif isinstance(a, dict) and "type" in a:
                        cleaned_actions.append(str(a["type"]))
                response_json["actions"] = cleaned_actions
            else:
                response_json["actions"] = []

            # Validasi Pydantic
            try:
                validated = GeminiStructuredResponse(**response_json)
                return validated.model_dump()
            except Exception as ve:
                response_json["schema_warning"] = f"Validation error: {str(ve)}"
                return response_json

        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)}"}

    def chat_with_history(self, user_message: str, history: List[Dict[str, str]], collected_entities: dict) -> dict:
        """
        Chat dengan conversation history + entity accumulation
        + handover detection + order redirect logic.
        """
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]

        known_entities = {k: v for k, v in collected_entities.items() if v is not None}
        if known_entities:
            known = ", ".join(f"{k}: {v}" for k, v in known_entities.items())
            messages.append({
                "role": "system",
                "content": f"Info yang sudah diketahui dari customer sejauh ini: {known}"
            })

        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Append anchor rule to user message
        messages.append({
            "role": "user",
            "content": f"{user_message}\n\n{ANCHOR_RULES}\n{JSON_FORMAT_INSTRUCTION}"
        })

        try:
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=messages,
                        max_tokens=LLM_MAX_TOKENS,
                        temperature=0.2,
                        top_p=0.9
                    )
                    break
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait_time = 2 ** attempt
                        print(f"[INFO] Rate limit tercapai, menunggu {wait_time}s... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")
                        time.sleep(wait_time)
                        if attempt == LLM_MAX_RETRIES - 1:
                            raise
                    else:
                        raise

            response_text = response.choices[0].message.content.strip()
            response_json = extract_json(response_text)

            if response_json:
                # Bersihkan intent
                raw_intent = str(response_json.get("intent", "other"))
                if raw_intent not in VALID_INTENTS:
                    first_candidate = re.split(r'[|,]', raw_intent)[0].strip()
                    response_json["intent"] = first_candidate if first_candidate in VALID_INTENTS else "other"

                # Bersihkan actions
                raw_actions = response_json.get("actions", [])
                if isinstance(raw_actions, list):
                    cleaned_actions = []
                    for a in raw_actions:
                        if isinstance(a, str):
                            cleaned_actions.append(a)
                        elif isinstance(a, dict) and "type" in a:
                            cleaned_actions.append(str(a["type"]))
                    response_json["actions"] = cleaned_actions
                else:
                    response_json["actions"] = []

                # Update & akumulasi entities
                new_entities = response_json.get("entities", {}) or {}
                updated_entities = dict(collected_entities)
                for k, v in new_entities.items():
                    if v is not None and k in updated_entities:
                        updated_entities[k] = v
                response_json["entities"] = updated_entities

                # --- Jika customer mau order, arahkan ke web ---
                cur_intent = response_json.get("intent", "")
                cur_purchase_intent = response_json.get("purchase_intent", "")

                if cur_intent == "ordering" or cur_purchase_intent == "ready_to_order":
                    base_reply = response_json.get("reply", "").rstrip()
                    response_json["reply"] = (
                        f"{base_reply}\n\n"
                        f"Untuk melanjutkan pemesanan, silakan melalui halaman web kami ya kak 🛒✨\n"
                        f"👉 {ORDER_WEB_URL}"
                    )
                    if "redirect_to_web" not in response_json.get("actions", []):
                        response_json.setdefault("actions", []).append("redirect_to_web")

                # --- Cek needs_handover dari model, lalu terapkan safety-net override ---
                needs_handover = bool(response_json.get("needs_handover", False))
                handover_reason = response_json.get("handover_reason")

                override_reason = check_handover_override(user_message, updated_entities)
                if override_reason and not needs_handover:
                    needs_handover = True
                    handover_reason = override_reason
                    # Ganti reply dengan pesan aman generik
                    response_json["reply"] = (
                        "Untuk permintaan ini, saya mau pastikan dulu dengan tim kami ya kak, "
                        "biar nggak salah info 🙏"
                    )

                response_json["needs_handover"] = needs_handover
                response_json["handover_reason"] = handover_reason if needs_handover else None

                if needs_handover:
                    admin = self._get_next_markom_admin()
                    wa_link = f"https://wa.me/{admin['phone']}"

                    response_json["assigned_admin"] = admin["name"]
                    response_json["handover_link"] = wa_link

                    base_reply = response_json.get("reply", "").rstrip()
                    response_json["reply"] = (
                        f"{base_reply}\n\nUntuk hal ini, saya hubungkan ke admin kami ya kak 🙏\n"
                        f"{admin['name']}: {wa_link}"
                    )

                    if "handover_admin" not in response_json.get("actions", []):
                        response_json.setdefault("actions", []).append("handover_admin")

                return response_json
            else:
                print(f"[WARNING] Could not parse JSON. Raw response:\n{response_text[:200]}\n")
                return {
                    "reply": response_text[:500],
                    "intent": "other",
                    "purchase_intent": "low",
                    "entities": dict(collected_entities),
                    "actions": [],
                    "needs_handover": False,
                    "handover_reason": None,
                    "warning": "Could not parse JSON - returning raw response"
                }

        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)}"}
