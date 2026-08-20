import json
import re
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from openai import OpenAI

from src.config import (
    LLM_API_KEY, 
    LLM_MODEL, 
    LLM_BASE_URL,
    LLM_MAX_TOKENS, 
    LLM_TEMPERATURE, 
    LLM_MAX_RETRIES,
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
    package_name: Optional[str] = None

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
    # Cek quantity dari entities ATAU dari pesan terakhir saja
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
    complaint_keywords = [
        r'\bkomplain\b', r'\bkeluhan\b', r'\bkecewa\b', 
        r'\btelat\b', r'\bterlambat\b', r'\bbasi\b', r'\brusak\b',
        r'\bsalah kirim\b', r'\btidak sesuai pesanan\b'
    ]
    if any(re.search(k, text) for k in complaint_keywords):
        return "Komplain terhadap pesanan yang sudah berjalan"

    return None

class LLMService:
    """Centralized LLM client menggunakan OpenAI SDK."""
    
    def __init__(self):
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
        self.system_prompt = build_system_prompt()
        self._markom_round_robin_counter = {"index": 0}

    def _get_next_markom_admin(self):
        """Pilih admin Markom berikutnya secara round-robin"""
        idx = self._markom_round_robin_counter["index"] % len(MARKOM_ADMINS)
        admin = MARKOM_ADMINS[idx]
        self._markom_round_robin_counter["index"] += 1
        return admin

    def simple_chat(self, user_message: str) -> str:
        """Chat sederhana, return plain text response."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message}
        ]

        response = self.client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=300
        )
            
        response_text = response.choices[0].message.content.strip()
        return clean_markdown(response_text)

    def chat_structured(self, user_message: str) -> dict:
        """Chat dengan structured JSON output, divalidasi Pydantic."""
        
        json_format_broad = """Format HANYA JSON. Gunakan struktur ini:
{
  "reply": "response in Indonesian",
  "intent": "product_inquiry",
  "purchase_intent": "low",
  "entities": {
    "quantity": null,
    "budget_per_box": null,
    "event_type": null,
    "location": null,
    "event_date": null,
    "customer_name": null,
    "customer_phone": null,
    "package_name": null
  },
  "actions": ["show_products"],
  "needs_handover": false,
  "handover_reason": null
}

CATATAN:
- intent: pilih TEPAT SATU dari (greeting, product_inquiry, price_inquiry, recommendation, ordering, other)
- purchase_intent: pilih TEPAT SATU dari (low, medium, high, ready_to_order)
- entities: isi dengan value yang sesuai (bisa berupa angka untuk quantity/budget_per_box, string untuk lainnya) atau null.
"""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"{user_message}\n\nRespond ONLY as valid JSON in this format:\n{json_format_broad}"}
        ]

        try:
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    response = self.client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=messages,
                        max_tokens=LLM_MAX_TOKENS,
                        temperature=LLM_TEMPERATURE
                    )
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    is_rate_limit = "rate_limit" in err_str or "429" in err_str
                    # gpt-oss kadang gagal validasi JSON karena reasoning token
                    # menghabiskan budget max_tokens sebelum sampai ke completion
                    # akhir. Ini seringnya transient, jadi layak di-retry juga.
                    is_json_validate_fail = "json_validate_failed" in err_str

                    if is_rate_limit or is_json_validate_fail:
                        if is_rate_limit:
                            wait_time = 5 * (attempt + 1)  # Default 5, 10, 15 detik
                            match = re.search(r'try again in (\d+\.?\d*)s', err_str)
                            if match:
                                wait_time = float(match.group(1)) + 1.0 # Tambah 1 detik buffer
                            print(f"[INFO] Rate limit tercapai, menunggu {wait_time:.1f}s sebelum coba lagi... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")
                        else:
                            wait_time = 1.0
                            print(f"[INFO] JSON validation gagal (kemungkinan reasoning token gpt-oss kehabisan budget), coba lagi... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")

                        time.sleep(wait_time)
                        if attempt == LLM_MAX_RETRIES - 1:
                            print(f"[ERROR] Max retries reached for chat_structured: {str(e)}")
                            raise
                    else:
                        print(f"[ERROR] Unknown error in chat_structured: {str(e)}")
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

    def chat_with_history(self, user_message: str, history: List[Dict[str, str]], collected_entities: dict, raw_user_message: Optional[str] = None) -> dict:
        """
        Chat dengan conversation history + entity accumulation
        + handover detection + order redirect logic.

        user_message: pesan yang dikirim ke LLM, boleh sudah di-augment dengan
            konteks RAG (mis. diawali "[KONTEKS DARI KNOWLEDGE BASE]...").
        raw_user_message: pesan ASLI dari customer TANPA konteks RAG, dipakai
            untuk safety-net keyword check (check_handover_override) supaya
            fungsi itu tidak ikut men-scan isi knowledge base sebagai kalau
            itu perkataan customer. Jika tidak diisi, fallback ke user_message.
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
                        temperature=LLM_TEMPERATURE,
                        response_format={"type": "json_object"}
                    )
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    is_rate_limit = "rate_limit" in err_str or "429" in err_str
                    # gpt-oss kadang gagal validasi JSON karena reasoning token
                    # menghabiskan budget max_tokens sebelum sampai ke completion
                    # akhir (failed_generation kosong). Ini seringnya transient,
                    # jadi layak di-retry juga, bukan langsung dianggap fatal.
                    is_json_validate_fail = "json_validate_failed" in err_str

                    if is_rate_limit or is_json_validate_fail:
                        if is_rate_limit:
                            wait_time = 5 * (attempt + 1)
                            match = re.search(r'try again in (\d+\.?\d*)s', err_str)
                            if match:
                                wait_time = float(match.group(1)) + 1.0
                            print(f"[INFO] Rate limit tercapai, menunggu {wait_time:.1f}s... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")
                        else:
                            wait_time = 1.0
                            print(f"[INFO] JSON validation gagal (kemungkinan reasoning token gpt-oss kehabisan budget), coba lagi... (percobaan {attempt+1}/{LLM_MAX_RETRIES})")

                        time.sleep(wait_time)
                        if attempt == LLM_MAX_RETRIES - 1:
                            print(f"[ERROR] Max retries reached for chat_with_history: {str(e)}")
                            raise
                    else:
                        print(f"[ERROR] Unknown error in chat_with_history: {str(e)}")
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
                        # Untuk quantity: jangan override ke nilai lebih kecil kecuali
                        # intent menunjukkan perubahan pesanan (bukan subset)
                        if k == "quantity" and updated_entities.get(k) is not None:
                            old_val = updated_entities[k]
                            if isinstance(old_val, (int, float)) and isinstance(v, (int, float)):
                                if v < old_val and response_json.get("intent") != "ordering":
                                    continue  # Skip: kemungkinan subset, bukan total baru
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

                # Jangan override handover jika customer sedang ordering (bukan komplain)
                override_reason = None
                if cur_intent not in ("ordering",):
                    override_reason = check_handover_override(raw_user_message or user_message, updated_entities)
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
                    "reply": response_text,
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