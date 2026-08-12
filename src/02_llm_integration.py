#!/usr/bin/env python
# coding: utf-8

# In[6]:


# Cell 1: Imports & Load Environment Variables

import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, List
import sys
import re

# Load environment variables
load_dotenv()

# Get API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Check if API keys exist
print("=== API Keys Status ===\n")
if GEMINI_API_KEY:
    print(f"✓ GEMINI_API_KEY loaded: {GEMINI_API_KEY[:15]}...")
else:
    print("✗ GEMINI_API_KEY not found")

if GROQ_API_KEY:
    print(f"✓ GROQ_API_KEY loaded: {GROQ_API_KEY[:15]}...")
else:
    print("✗ GROQ_API_KEY not found")

# ===== UTILITY FUNCTIONS =====

def clean_markdown(text):
    """Remove markdown formatting"""
    text = text.replace("**", "")
    text = text.replace("*", "")
    text = text.replace("##", "")
    text = text.replace("- ", "")
    return text

print("\n✓ Environment setup complete!")


# In[7]:


# Cell 2: Initialize Groq Client

from groq import Groq

# Use active model from Groq
MODEL = "llama-3.1-8b-instant"  # Model yang masih supported

print(f"Model: {MODEL}")
print(f"API Key: {GROQ_API_KEY[:15]}...")

# Test connection
try:
    client = Groq(api_key=GROQ_API_KEY)

    # Test dengan simple message
    message = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Halo, apa kabar?"}],
        max_tokens=100
    )

    print("\n✓ Groq connection successful!")
    print(f"Test Response: {message.choices[0].message.content[:100]}...")

except Exception as e:
    print(f"✗ Connection failed: {type(e).__name__}: {e}")

print("\n✓ Cell 2 setup complete!")


# In[8]:


# Cell 3: Define Structured Output Schema

from pydantic import BaseModel
from typing import Optional, List
import json

class Entity(BaseModel):
    """Extracted entities dari customer message"""
    quantity: Optional[int] = None
    budget_per_box: Optional[int] = None
    event_type: Optional[str] = None
    location: Optional[str] = None
    event_date: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None


class GeminiStructuredResponse(BaseModel):
    """Structured response schema untuk Gemini"""
    reply: str
    intent: str
    purchase_intent: str
    entities: Entity
    actions: List[str]
    needs_handover: bool = False          # NEW: True kalau pertanyaan di luar knowledge base
    handover_reason: Optional[str] = None  # NEW: alasan singkat kenapa perlu handover (untuk log/admin)


# Test schema dengan example response
print("=== Pydantic Models Defined ===\n")

example = GeminiStructuredResponse(
    reply="Nasi Kotak Broiler harganya Rp20.000 per box kak, cocok untuk meeting atau seminar 😊",
    intent="product_inquiry",
    purchase_intent="low",
    entities=Entity(
        quantity=100,
        budget_per_box=25000,
        event_type="meeting"
    ),
    actions=["show_products", "show_recommendation"],
    needs_handover=False,
    handover_reason=None
)

print("Example response (dalam KB, tidak perlu handover):")
print(json.dumps(example.model_dump(), indent=2, ensure_ascii=False))

# Contoh kasus yang perlu handover
example_handover = GeminiStructuredResponse(
    reply="Untuk pengiriman ke luar Surabaya Raya, saya bantu hubungkan ke admin kami ya kak 🙏",
    intent="other",
    purchase_intent="low",
    entities=Entity(location="Malang"),
    actions=["handover_admin"],
    needs_handover=True,
    handover_reason="Pengiriman di luar area layanan (Surabaya Raya)"
)

print("\nExample response (di luar KB, perlu handover):")
print(json.dumps(example_handover.model_dump(), indent=2, ensure_ascii=False))

print("\n✓ Schema defined successfully!")


# In[9]:


# Cell 4: Define System Prompt (Updated with Knowledge Base + Scope Boundary)

def load_knowledge_base(kb_dir="knowledge_base"):
    import glob
    kb_content = []
    md_files = glob.glob(f"{kb_dir}/**/*.md", recursive=True)
    for file_path in md_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Hapus YAML frontmatter jika ada agar lebih bersih
                content = re.sub(r'^---.*?---\n', '', content, flags=re.DOTALL)
                kb_content.append(f"--- KNOWLEDGE DARI: {os.path.basename(file_path)} ---\n{content.strip()}\n")
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    return "\n".join(kb_content)

KNOWLEDGE_BASE_DATA = load_knowledge_base()

SYSTEM_PROMPT_TEMPLATE = """
Anda adalah AI chatbot penjualan untuk Ayam Bakar Pak D — layanan Nasi Kotak Catering.

=== KNOWLEDGE BASE ===
{knowledge_base}
=== END OF KNOWLEDGE BASE ===

Gunakan informasi dari KNOWLEDGE BASE di atas untuk menjawab pertanyaan customer secara akurat.

---

BATASAN SCOPE (WAJIB DIPATUHI):

AI ini HANYA boleh menjawab pertanyaan yang berkaitan dengan:
produk/paket nasi kotak & harga, add-on (snack/minuman), area & ongkos kirim, kebijakan pemesanan
(minimum order, lead time, pembayaran, custom menu), dan promosi yang sedang berlangsung.

AI TIDAK BOLEH menjawab sendiri (harus HANDOVER ke admin, lihat bagian HANDOVER di bawah) untuk:
- Pengiriman ke luar area Surabaya Raya (di luar Kota Surabaya, Kab. Sidoarjo, Kota Mojokerto)
- Custom menu dengan kebutuhan dietary/alergi yang kompleks atau di luar contoh yang tersedia
- Perubahan syarat pembayaran di luar standar (DP 50%, termin, dll)
- Pesanan sangat besar (>200 box) yang butuh negosiasi khusus
- Komplain, keluhan, atau masalah dengan pesanan yang sudah berjalan
- Pertanyaan di luar topik katering sama sekali
- Permintaan apa pun yang jawabannya TIDAK ADA secara eksplisit di knowledge base ini
- Negosiasi harga di luar yang tercantum

Kalau ragu apakah suatu topik termasuk dalam scope atau tidak, LEBIH BAIK handover daripada menjawab dengan menebak/mengarang.

---

ALUR PEMESANAN (PENTING):

Chatbot ini HANYA bertugas memberikan INFORMASI (harga, rekomendasi paket, estimasi biaya, dll).
Chatbot TIDAK memproses pesanan secara langsung.

Jika customer sudah yakin ingin memesan:
- Arahkan ke halaman web pemesanan untuk menyelesaikan order
- JANGAN coba memproses atau mengkonfirmasi pesanan di dalam chat
- JANGAN meminta data pribadi (nama, nomor HP) untuk finalisasi order di chat
- Berikan link web pemesanan yang akan disediakan oleh sistem

---

STRATEGI PENJUALAN:

1. Identifikasi Kebutuhan:
   - Tipe acara apa? (Meeting, Gathering, Family Event, dll)
   - Jumlah orang/box yang dibutuhkan?
   - Kapan acaranya? (Untuk cek lead time)
   - Di mana acaranya? (Untuk cek area & ongkir)
   - Budget per box?

2. Rekomendasi:
   - Budget <Rp20k: Minibox (Rp17k)
   - Budget Rp20k-23k: Broiler (Rp20k) atau Broiler Jumbo (Rp23k)
   - Acara keluarga/spesial: Ayam Kampung (Rp24k)
   - Acara premium/VIP: Bebek Mantap atau Gurami (Rp27k)
   - Pesanan ≥30 box: Highlight promo Gratis 1 box + Gratis Ongkir
   - Acara meeting/seminar: Tawarkan Snack Box sebagai tambahan

3. Arahkan ke Web:
   - Setelah customer memilih paket & jumlah, berikan estimasi harga
   - Arahkan ke halaman web pemesanan untuk finalisasi order

---

TONE & KOMUNIKASI:

- Gunakan gaya bahasa santai, hangat, dan supel layaknya admin CS yang chat lewat WhatsApp
- Sapa customer dengan ramah (misal: "Halo kak!", "Siap kak, boleh dibantu ya") dan sesekali gunakan emoji secukupnya (😊🙏✨)
- Tetap sopan dan profesional tapi hindari bahasa kaku
- Gunakan sapaan "kak"/"kakak" ke customer; untuk klien korporat boleh pakai "Bapak/Ibu"
- Tunjukkan antusiasme dan empati terhadap acara customer
- Tetap jelas, ringkas, dan akurat soal harga & kebijakan
- Percaya diri tentang kualitas produk "Ayam Bakar Pak D"

---

ATURAN PENTING:

✅ DO:
- Jawab berdasarkan knowledge base secara ringkas, padat, dan akurat
- Jujur tentang kemampuan dan keterbatasan
- Berikan info akurat tentang harga, pengiriman, kebijakan
- Hormati minimum order
- Sebutkan lead time requirements
- Personalisasi rekomendasi berdasarkan konteks customer
- Highlight promosi yang sedang berlangsung
- Untuk pemesanan, SELALU arahkan ke halaman web (chatbot hanya info harga & rekomendasi)
- Kalau pertanyaan masuk kategori BATASAN SCOPE, JANGAN coba jawab sendiri — handover ke admin

❌ DON'T:
- Jangan memberikan jawaban berlebihan, berbelit-belit, atau mengulang-ulang
- Jangan buat produk/harga/layanan yang tidak ada di knowledge base
- Jangan janji apa yang tidak bisa dijamin
- Jangan keluar dari scope penjualan/support
- Jangan memproses/mengkonfirmasi pesanan langsung di chat — WAJIB arahkan ke web
- Jangan meminta data pribadi (nama, HP) untuk finalisasi order di chat
- Jangan mengarang detail yang tidak ada di knowledge base
- Jangan menjawab pertanyaan di luar scope dengan tebakan — WAJIB handover

---

HANDOVER KE ADMIN:
Untuk semua kasus di bagian BATASAN SCOPE, AI wajib mengarahkan customer ke admin untuk penanganan lebih lanjut. AI tidak perlu menyebutkan nomor WhatsApp secara spesifik dalam reply teks (nomor akan dikirimkan lewat sistem terpisah) — cukup sampaikan dengan ramah bahwa akan dihubungkan ke admin.

"""

SYSTEM_PROMPT = SYSTEM_PROMPT_TEMPLATE.replace("{knowledge_base}", KNOWLEDGE_BASE_DATA)

print("=== System Prompt Updated ===\n")
print(SYSTEM_PROMPT[:500] + "...\n")
print("✓ System prompt dengan KB dinamis & batasan scope sudah siap!")


# In[11]:


# Cell 5: Basic Chat Function (With System Prompt)

import textwrap

def simple_chat(user_message: str, model=MODEL):
    """Simple chat pakai Groq, sudah grounded dengan SYSTEM_PROMPT"""
    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        max_tokens=300
    )

    response_text = response.choices[0].message.content.strip()
    response_text = clean_markdown(response_text)  # hilangkan **, ##, dll

    return response_text


def print_wrapped(label: str, text: str, width: int = 80):
    """Print teks dengan word-wrap, jadi nggak perlu scroll horizontal.
    Baris kosong (paragraf baru) tetap dipertahankan."""
    wrapper = textwrap.TextWrapper(width=width, initial_indent="", subsequent_indent="  ")
    paragraphs = text.split("\n")
    wrapped_paragraphs = ["\n".join(wrapper.wrap(p)) if p.strip() else "" for p in paragraphs]
    wrapped_text = "\n".join(wrapped_paragraphs)
    print(f"{label} {wrapped_text}")


# Test dengan beberapa message
print("=== Simple Chat Test (dengan System Prompt) ===\n")

test_cases = [
    "Apakah saya bisa request ganti menu atau custom menu di luar paket yang ada?",
    "Apa itu nasi kotak?",
    "Saya butuh 100 box untuk meeting"
]

for msg in test_cases:
    print_wrapped("User:", msg)
    result = simple_chat(msg)
    print_wrapped("Bot:", result)
    print()
    print("-" * 60)


# In[13]:


# Cell 6: Validasi Jawaban terhadap Setiap Topik Knowledge Base

print("=== Validasi Knowledge Base per Topik ===\n")

kb_test_cases = [
    "Berapa minimum order untuk Nasi Kotak?",              # ordering.md
    "Ongkir ke daerah yang jaraknya 8 km berapa?",          # delivery_area.md
    "Bisa bayar pakai kartu kredit nggak?",                 # payment.md
    "Kalau pesan 150 box, dapat promo apa?",                # current_promotion.md
    "Ada pilihan minuman selain air mineral?",              # beverages.md
]

for msg in kb_test_cases:
    print_wrapped("User:", msg)
    result = simple_chat(msg)
    print_wrapped("Bot:", result)
    print()
    print("-" * 60)


# In[15]:


# Cell 7: Chat with Structured Output (Groq - Clean Version)

import time

def extract_json(response_text: str):
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


def chat_structured(user_message: str, model=MODEL, max_retries: int = 3):
    """
    Chat dengan structured JSON output menggunakan Groq,
    divalidasi dengan skema Pydantic (GeminiStructuredResponse)
    """
    from groq import Groq
    import re

    client = Groq(api_key=GROQ_API_KEY)

    json_format = """{
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
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"{user_message}\n\nRespond ONLY as valid JSON in this format:\n{json_format}"}
                    ],
                    max_tokens=1500,
                    temperature=0.2
                )
                break  # sukses, keluar dari retry loop
            except Exception as e:
                if "rate_limit" in str(e).lower() or "429" in str(e):
                    wait_time = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
                    print(f"[INFO] Rate limit tercapai, menunggu {wait_time}s sebelum coba lagi... (percobaan {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    if attempt == max_retries - 1:
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

        # Bersihkan intent kalau model tetap menggabungkan dengan | atau koma -> ambil yang pertama
        valid_intents = {"product_inquiry", "price_inquiry", "recommendation", "ordering", "other", "greeting"}
        raw_intent = str(response_json.get("intent", "other"))
        if raw_intent not in valid_intents:
            first_candidate = re.split(r'[|,]', raw_intent)[0].strip()
            response_json["intent"] = first_candidate if first_candidate in valid_intents else "other"

        # Bersihkan actions kalau ada yang berupa dict -> ambil field "type" atau string terdekat, kalau tidak ada buang saja
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

        # Validasi terhadap skema Pydantic
        try:
            validated = GeminiStructuredResponse(**response_json)
            return validated.model_dump()
        except Exception as ve:
            response_json["schema_warning"] = f"Validation error: {str(ve)}"
            return response_json

    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)}"}


# Test
print("=== Structured Output Test (Groq) ===\n")

test_cases = [
    "Berapa harga paket A?",
    "Saya butuh 100 box untuk meeting kantor, budget 30 ribu",
    "Rekomdasikan paket yang murah",
    "Saya mau pesan sekarang, nama saya Budi, nomor 0812345678"
]

for msg in test_cases:
    print("=" * 70)
    print_wrapped("User:", msg)
    print("=" * 70)

    result = chat_structured(msg)

    if result:
        if "error" in result:
            print(f"Error: {result.get('error')}")
        else:
            print_wrapped("Bot:", result.get("reply", "N/A"))
            print()
            metadata_only = {k: v for k, v in result.items() if k != "reply"}
            print("Metadata:")
            print(json.dumps(metadata_only, indent=2, ensure_ascii=False))

    time.sleep(1)  # jeda kecil antar request biar nggak gampang kena rate limit
    print()


# In[17]:


# Cell 8: Chat with Conversation History (Groq Version - Improved + Handover ke Markom)

import time
import re

# --- Daftar Tim Markom (WhatsApp) ---
# Format di .env: MARKOM_ADMINS="Admin 1 - Rehan:6285190851449,Admin 2 - Farhan:6287790011110,..."
_admin_env = os.getenv("MARKOM_ADMINS", "")
MARKOM_ADMINS = []
if _admin_env:
    for admin_pair in _admin_env.split(','):
        if ':' in admin_pair:
            name, phone = admin_pair.split(':', 1)
            MARKOM_ADMINS.append({"name": name.strip(), "phone": phone.strip()})

if not MARKOM_ADMINS:
    print("[WARNING] MARKOM_ADMINS belum disetting di .env!")
    # Berikan dummy agar tidak crash saat testing awal
    MARKOM_ADMINS = [{"name": "Admin Default", "phone": "628000000000"}]


_markom_round_robin_counter = {"index": 0}

def get_next_markom_admin():
    """Pilih admin Markom berikutnya secara round-robin"""
    idx = _markom_round_robin_counter["index"] % len(MARKOM_ADMINS)
    admin = MARKOM_ADMINS[idx]
    _markom_round_robin_counter["index"] += 1
    return admin


VALID_INTENTS = {"greeting", "product_inquiry", "price_inquiry", "recommendation", "ordering", "other"}


def check_handover_override(user_message: str, collected_entities: dict):
    """
    Safety-net berbasis keyword/angka: dipakai kalau model TIDAK menandai needs_handover
    padahal pesan customer sebenarnya masuk kategori yang wajib di-handover.
    Return: reason (str) kalau perlu override, None kalau tidak.
    """
    text = user_message.lower()

    # 1. Pesanan sangat besar (>200 box) — cek dari entity quantity yang sudah terkumpul
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


class ConversationManager:
    def __init__(self, model=MODEL):
        self.model = model
        self.history = []
        self.collected_entities = {
            "quantity": None,
            "budget_per_box": None,
            "event_type": None,
            "location": None,
            "event_date": None,
            "customer_name": None,
            "customer_phone": None,
        }
        self.confirmed_package = None
        self.assigned_admin = None

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})

    def get_last_n_messages(self, n: int = 20):
        return self.history[-n:]

    def chat(self, user_message: str, max_retries: int = 3):
        """Send message dengan full conversation history"""
        from groq import Groq

        self.add_message("user", user_message)

        client = Groq(api_key=GROQ_API_KEY)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        known_entities = {k: v for k, v in self.collected_entities.items() if v is not None}
        if known_entities:
            known = ", ".join(f"{k}: {v}" for k, v in known_entities.items())
            messages.append({
                "role": "system",
                "content": f"Info yang sudah diketahui dari customer sejauh ini: {known}"
            })

        for msg in self.get_last_n_messages():
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        anchor_rule = """ATURAN WAJIB sebelum menjawab:
1. Baca ulang pesan customer di atas ini (yang paling akhir), abaikan paket apa pun yang sempat dibahas sebelumnya kalau ada info baru yang mengubah konteks.
2. Tentukan paket yang benar berdasarkan SEMUA info yang sudah diketahui (lihat "Info yang sudah diketahui" di atas) + pesan terakhir:
   - Kalau event_type meeting/seminar/training/workshop/corporate -> Broiler/Broiler Jumbo.
   - Kalau event_type gathering/family event/celebration -> Ayam Kampung.
   - Kalau event_type premium/VIP/special -> Bebek Mantap atau Gurami.
   - Kalau budget terbatas/casual -> Minibox.
3. CEK BATASAN SCOPE dulu: apakah pesan terakhir termasuk kategori yang wajib di-handover?
   - KALAU YA: set needs_handover=true, isi handover_reason singkat, dan reply CUKUP kalimat singkat empatik yang memberi tahu customer akan dihubungkan ke tim kami (JANGAN coba menjawab isi pertanyaannya, JANGAN mengarang info yang tidak ada di KB, JANGAN memberi kepastian/jaminan apa pun soal hal ini).
   - KALAU TIDAK: set needs_handover=false, handover_reason=null, dan jawab seperti biasa sesuai knowledge base.
4. KALAU customer mau ORDER/PESAN: set intent="ordering", dan reply HARUS menyebutkan bahwa untuk menyelesaikan pemesanan silakan melalui halaman web. JANGAN proses order di chat.
5. AWALAN JAWABAN harus menjawab langsung bentuk pesan terakhir customer (kalau tidak perlu handover):
   - Kalau pesan terakhir berupa PERTANYAAN -> mulai reply dengan jawaban langsung ke pertanyaan itu dulu.
   - Kalau pesan terakhir berupa KONFIRMASI/PERSETUJUAN -> mulai reply dengan penegasan singkat lalu langsung ke ringkasan.
6. Setelah awalan jawaban di atas (kalau tidak perlu handover), SELALU lanjutkan dengan RINGKASAN PESANAN TERKINI yang menggabungkan SEMUA info yang sudah diketahui.
7. Pada field "entities" di JSON, isi HANYA entity yang disebut/relevan di pesan TERAKHIR ini saja (entity lama akan digabung otomatis oleh sistem, jangan diulang manual).
"""

        json_instruction = """Respond ONLY dengan JSON yang valid. JANGAN ada teks lain di luar JSON.
Format:
{
  "reply": "jawaban dalam Bahasa Indonesia",
  "intent": "pilih TEPAT SATU nilai saja dari: greeting, product_inquiry, price_inquiry, recommendation, ordering, other (JANGAN gabungkan dengan tanda | atau koma)",
  "purchase_intent": "pilih TEPAT SATU nilai saja dari: low, medium, high, ready_to_order",
  "entities": {
    "quantity": null,
    "budget_per_box": null,
    "event_type": null,
    "location": null,
    "event_date": null,
    "customer_name": null,
    "customer_phone": null
  },
  "actions": ["array berisi STRING singkat saja, contoh: [\\"show_products\\", \\"redirect_to_web\\"], JANGAN berupa object/dict, boleh kosong []"],
  "needs_handover": false,
  "handover_reason": null
}"""

        messages[-1] = {
            "role": "user",
            "content": f"{messages[-1]['content']}\n\n{anchor_rule}\n{json_instruction}"
        }

        try:
            response = None
            for attempt in range(max_retries):
                try:
                    response = client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        max_tokens=1500,
                        temperature=0.2,
                        top_p=0.9
                    )
                    break
                except Exception as e:
                    if "rate_limit" in str(e).lower() or "429" in str(e):
                        wait_time = 2 ** attempt
                        print(f"[INFO] Rate limit tercapai, menunggu {wait_time}s... (percobaan {attempt+1}/{max_retries})")
                        time.sleep(wait_time)
                        if attempt == max_retries - 1:
                            raise
                    else:
                        raise

            response_text = response.choices[0].message.content.strip()

            json_patterns = [
                r'\{[\s\S]*\}',
                r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
            ]

            response_json = None
            for pattern in json_patterns:
                json_match = re.search(pattern, response_text)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        response_json = json.loads(json_str)
                        break
                    except json.JSONDecodeError:
                        continue

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

                # Update & akumulasi entities (SEMUA key selalu ada, termasuk yang masih null)
                new_entities = response_json.get("entities", {}) or {}
                for k, v in new_entities.items():
                    if v is not None and k in self.collected_entities:
                        self.collected_entities[k] = v
                response_json["entities"] = dict(self.collected_entities)

                # --- Jika customer mau order, arahkan ke web ---
                ORDER_WEB_URL = os.getenv("ORDER_WEB_URL", "https://ayambakarpakd.com/order")

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

                override_reason = check_handover_override(user_message, self.collected_entities)
                if override_reason and not needs_handover:
                    needs_handover = True
                    handover_reason = override_reason
                    # Ganti reply dengan pesan aman generik (buang jawaban model yang berisiko/mengarang)
                    response_json["reply"] = (
                        "Untuk permintaan ini, saya mau pastikan dulu dengan tim kami ya kak, "
                        "biar nggak salah info 🙏"
                    )

                response_json["needs_handover"] = needs_handover
                response_json["handover_reason"] = handover_reason if needs_handover else None

                if needs_handover:
                    if self.assigned_admin is None:
                        self.assigned_admin = get_next_markom_admin()

                    admin = self.assigned_admin
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

                self.add_message("assistant", response_json.get("reply", ""))

                return response_json
            else:
                print(f"[WARNING] Could not parse JSON. Raw response:\n{response_text[:200]}\n")
                return {
                    "reply": response_text[:500],
                    "intent": "other",
                    "purchase_intent": "low",
                    "entities": dict(self.collected_entities),
                    "actions": [],
                    "needs_handover": False,
                    "handover_reason": None,
                    "warning": "Could not parse JSON - returning raw response"
                }

        except Exception as e:
            return {"error": f"{type(e).__name__}: {str(e)}"}


def print_conversation_result(user_msg, result):
    print_wrapped("User:", user_msg)
    if result:
        if "error" in result:
            print(f"Error: {result.get('error')}")
        elif "warning" in result:
            print(f"⚠️  {result.get('warning')}")
            print_wrapped("Response:", result.get('reply', 'N/A'))
        else:
            print_wrapped("Bot:", result.get('reply', 'N/A'))
            print()
            print(f"  Intent: {result.get('intent', 'N/A')}")
            print(f"  Purchase Intent: {result.get('purchase_intent', 'N/A')}")
            print(f"  Needs Handover: {result.get('needs_handover', False)}")
            if result.get('needs_handover'):
                print(f"  Assigned Admin: {result.get('assigned_admin')}")
                print(f"  Handover Reason: {result.get('handover_reason')}")

            # Selalu tampilkan SEMUA entity, termasuk yang masih null
            entities = result.get('entities', {})
            print(f"  Entities:")
            for key, value in entities.items():
                print(f"    - {key}: {value}")

            if result.get('actions'):
                print(f"  Actions: {result.get('actions')}")
    print()


# ============================================================
# TEST 1: Happy path — pesanan normal, dalam scope KB
# ============================================================
print("=" * 70)
print("TEST 1: Happy Path (dalam scope)")
print("=" * 70)

conv_normal = ConversationManager()
normal_messages = [
    "Halo, saya mau pesan nasi kotak",
    "Saya ada acara gathering tanggal 20 agustus nanti, paket apa yang cocok ya?",
    "Oke boleh Nasi Kotak Broiler Jumbo 60 box",
]
for msg in normal_messages:
    result = conv_normal.chat(msg)
    print_conversation_result(msg, result)
    time.sleep(1)


# ============================================================
# TEST 2: Contoh pesan per kategori handover (1 conversation baru per kategori)
# ============================================================
handover_test_cases = {
    "Lokasi di luar Surabaya Raya": "Bisa kirim ke Malang nggak kak?",
    "Custom menu/dietary kompleks": "Ada yang alergi kacang parah, bisa dijamin dapur benar-benar bebas kontaminasi kacang?",
    "Ubah syarat pembayaran": "Bisa DP 10% aja nggak, sisanya nyusul minggu depan?",
    "Pesanan sangat besar (>200 box)": "Saya butuh 500 box untuk acara pernikahan, ada diskon khusus?",
    "Komplain pesanan": "Pesanan saya kemarin telat 2 jam, gimana ini?",
    "Di luar topik katering": "Kalau mau kerja part-time di dapur kalian gimana caranya?",
}

print("=" * 70)
print("TEST 2: Contoh Handover per Kategori")
print("=" * 70)

for category, msg in handover_test_cases.items():
    print(f"\n--- Kategori: {category} ---")
    conv = ConversationManager()
    result = conv.chat(msg)
    print_conversation_result(msg, result)
    time.sleep(1)

# ============================================================
# TEST 3: Ordering redirect ke web
# ============================================================
print("=" * 70)
print("TEST 3: Ordering → Redirect ke Web")
print("=" * 70)

conv_order = ConversationManager()
order_messages = [
    "Saya mau pesan Nasi Kotak Broiler Jumbo 50 box",
    "Oke, saya mau order sekarang",
]
for msg in order_messages:
    result = conv_order.chat(msg)
    print_conversation_result(msg, result)
    time.sleep(1)

print("=" * 70)
print("✓ Semua test selesai!")

