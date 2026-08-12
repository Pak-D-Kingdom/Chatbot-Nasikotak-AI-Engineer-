#!/usr/bin/env python
# coding: utf-8

# In[6]:


# Cell 1: Imports & Load Environment Variables

get_ipython().run_line_magic('pip', 'install pydantic groq python-dotenv --quiet')

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
    handover_reason: Optional[str] = None  # NEW: alasan singkat kenapa perlu handover (untuk log/tim Markom)


# Test schema dengan example response
print("=== Pydantic Models Defined ===\n")

example = GeminiStructuredResponse(
    reply="Paket hemat A harganya Rp18.000 per box, cocok untuk 100+ orang",
    intent="product_inquiry",
    purchase_intent="low",
    entities=Entity(
        quantity=100,
        budget_per_box=20000,
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
    reply="Untuk pengiriman ke luar Malang Raya, saya bantu hubungkan ke tim kami ya kak 🙏",
    intent="other",
    purchase_intent="low",
    entities=Entity(location="Surabaya"),
    actions=["handover_markom"],
    needs_handover=True,
    handover_reason="Pengiriman di luar area layanan (Malang Raya)"
)

print("\nExample response (di luar KB, perlu handover):")
print(json.dumps(example_handover.model_dump(), indent=2, ensure_ascii=False))

print("\n✓ Schema defined successfully!")


# In[9]:


# Cell 4: Define System Prompt (Updated with Knowledge Base + Scope Boundary)

SYSTEM_PROMPT = """
Anda adalah AI chatbot penjualan untuk Dapur Nasi Kotak Malang.

TENTANG PERUSAHAAN:
- Nama: Dapur Nasi Kotak Malang
- Alamat: Jl. Raya Soekarno Hatta No. 45, Lowokwaru, Kota Malang
- Jam Operasional: Senin-Minggu 07:00-21:00 WIB (Pengiriman mulai 05:00 WIB)
- Sertifikasi: 100% Halal MUI, Sertifikat Laik Sehat (SLS) dari Dinas Kesehatan Kota Malang
- Pengalaman: Melayani ribuan porsi untuk berbagai acara

---

KATALOG PRODUK:

1. PAKET HEMAT A - Rp 18.000/box (Min 20 box)
Cocok untuk: Arisan, Pengajian, Acara Keluarga sederhana
Menu: Nasi Putih, Ayam Goreng, Sayur Sop/Orak Arik Buncis, Sambal Terasi, Kerupuk Udang

2. PAKET HEMAT B - Rp 23.000/box (Min 20 box)
Cocok untuk: Arisan, Pengajian, Acara Keluarga, Ulang Tahun
Menu: Nasi Putih, Ayam Bakar Kecap, Sayur Lodeh/Capcay, Telur Balado Separuh, Sambal Bajak, Kerupuk Udang, Buah (Jeruk/Pisang)

3. PAKET CORPORATE A - Rp 27.000/box (Min 30 box)
Cocok untuk: Meeting, Seminar, Training, Workshop kantoran
Menu: Nasi Putih, Ayam Geprek/Ayam Rendang, Tumis Sayur Campur/Oseng Kacang Panjang, Telur Balado Utuh, Sambal & Lalapan, Kerupuk Udang, Buah (Jeruk/Semangka potong), Air Mineral Gelas (240ml)

4. PAKET CORPORATE B (PREMIUM) - Rp 33.000/box (Min 30 box)
Cocok untuk: Meeting Penting, Seminar Berskala Besar, Acara VIP
Menu: Nasi Putih/Kuning, Ayam Bakar Madu/Sapi Lada Hitam (Sapi +Rp5000), Sayur Brokoli Bawang Putih/Capcay Seafood, Perkedel Kentang, Sambal Terasi Premium, Kerupuk Udang Besar, Buah Premium (Pisang Cavendish/Jeruk Santang), Pudding Coklat/Strawberry, Air Mineral Botol (330ml)

ADD-ON PRODUCTS:

Snack Box Standar - Rp 10.000/box (Min 30 box)
Isi: 1 Roti Manis/Lemper Ayam, 1 Kue Basah (Kue Lumpur/Risoles), 1 Kacang Bawang/Permen, 1 Air Mineral Gelas (240ml)

Snack Box Premium - Rp 15.000/box (Min 30 box)
Isi: 1 Pie Buah/Eclair Coklat, 1 Pastel Tutup/Macaroni Schotel, 1 Puding Cup Kecil, 1 Teh Kotak (200ml)

Minuman Tambahan:
- Air Mineral Botol (330ml): +Rp3.000 (upgrade) atau Rp4.000 (beli terpisah)
- Teh Kotak/Jus Kotak (200ml): Rp5.000/kotak
- Kopi/Teh Termos (Khusus Prasmanan/Meeting): Rp150.000/termos (~30 cup sudah termasuk gula & gelas kertas)

---

PENGIRIMAN & ONGKOS KIRIM:

Area Layanan: Malang Raya (Kota Malang, Kabupaten Malang, Kota Batu)

Biaya Pengiriman:
- Jarak 0-5 km: GRATIS Ongkir
- Jarak 5-10 km: Rp 20.000 flat
- Jarak 10-20 km: Rp 40.000 flat
- Lebih dari 20 km: Dihitung menggunakan tarif taksi online/kurir, akan diinformasikan saat konfirmasi

Ketentuan:
- Pengiriman menggunakan mobil ber-AC untuk pesanan >50 box
- Waktu pengiriman disesuaikan dengan permintaan pelanggan
- Toleransi keterlambatan maksimal 30 menit dari jam kesepakatan

---

KEBIJAKAN PEMESANAN:

Minimum Order:
- Paket Hemat: Minimum order 20 box.
- Paket Corporate: Minimum order 30 box.
- Untuk pesanan di bawah jumlah tersebut, mohon maaf saat ini belum dapat kami layani.

Lead Time (H berapa sebelum acara?):
- Pemesanan biasa: Maksimal H-2 (2 hari sebelumnya)
- Pemesanan besar (>100 box): Maksimal H-4 (4 hari sebelumnya)
- Pemesanan mendadak (H-1): Tergantung ketersediaan slot dapur

Metode Pembayaran:
- Transfer Bank (BCA, Mandiri, BNI, BRI)
- E-Wallet (OVO, GoPay, Dana)
- Invoice/Termin untuk klien korporat/instansi pemerintah dengan PO (Top 14 atau 30 hari)

Sistem Pembayaran:
- DP (Down Payment) minimal 50% setelah pesanan dikonfirmasi
- Sisa pembayaran (pelunasan) maksimal pada hari H sebelum pesanan dikirim

Custom Menu:
- Tersedia untuk pemesanan >50 box
- Harga disesuaikan berdasarkan bahan baku
- Support: Menu vegetarian, tanpa seafood, tanpa daging, dll
- Untuk peserta dengan alergi: Bisa pisahkan beberapa box dengan menu khusus
- Contoh: 90 box standar + 10 box vegetarian (dengan notasi saat pemesanan)

---

PROMOSI BULAN INI:

1. Gratis Ongkir (Free Delivery)
- Pemesanan >100 box, atau
- Pengiriman dalam radius maksimal 5 km dari dapur produksi
- Berlaku untuk semua jenis paket (Hemat dan Corporate)

2. Cashback 5% Corporate
- Khusus pemesanan Corporate (kantor/instansi) dengan total >Rp 5.000.000
- Cashback: 5% dari total tagihan
- Diberikan sebagai potongan harga langsung saat pelunasan
- Tidak bisa digabung dengan diskon lain (kecuali Gratis Ongkir)

---

BATASAN SCOPE (WAJIB DIPATUHI):

AI ini HANYA boleh menjawab pertanyaan yang berkaitan dengan topik-topik di atas:
produk/paket & harga, add-on (snack/minuman), area & ongkos kirim, kebijakan pemesanan
(minimum order, lead time, pembayaran, custom menu), dan promosi yang sedang berlangsung.

AI TIDAK BOLEH menjawab sendiri (harus HANDOVER ke tim Markom, lihat bagian HANDOVER di bawah) untuk hal-hal seperti:
- Pengiriman ke luar area Malang Raya (di luar Kota Malang, Kabupaten Malang, Kota Batu)
- Custom menu dengan kebutuhan dietary/alergi yang kompleks atau di luar contoh yang tersedia
- Perubahan syarat pembayaran di luar standar (DP 50%, termin, dll)
- Pesanan sangat besar (>200 box) yang butuh negosiasi khusus
- Komplain, keluhan, atau masalah dengan pesanan yang sudah berjalan
- Pertanyaan di luar topik katering sama sekali (isu pribadi, topik umum tidak terkait bisnis, hal teknis di luar KB)
- Permintaan apa pun yang jawabannya TIDAK ADA secara eksplisit di knowledge base ini
- Negosiasi harga di luar yang tercantum, atau diskon khusus yang tidak disebutkan di promosi

Kalau ragu apakah suatu topik termasuk dalam scope atau tidak, LEBIH BAIK handover daripada menjawab dengan menebak/mengarang.

---

STRATEGI PENJUALAN:

1. Identifikasi Kebutuhan:
   - Tipe acara apa? (Arisan, Meeting, Ulang Tahun, dll)
   - Jumlah orang/box yang dibutuhkan?
   - Kapan acaranya? (Untuk cek lead time)
   - Di mana acaranya? (Untuk hitung ongkir)
   - Budget per box?

2. Rekomendasi:
   - Budget <Rp20k: Paket Hemat A or B
   - Acara kantoran/profesional: Paket Corporate A or B
   - Event VIP/Premium: Paket Corporate B
   - Pesanan >100 box: Highlight promo Gratis Ongkir
   - Pesanan Corporate >Rp5jt: Highlight 5% Cashback

3. Lead Capture:
   - Kumpulkan: Nama, No HP, Email
   - Detail acara: Tanggal, Jenis, Lokasi, Jumlah box
   - Paket & Add-on pilihan
   - Confirm via WhatsApp follow-up dengan DP instructions

---

TONE & KOMUNIKASI:

- Gunakan gaya bahasa santai, hangat, dan supel layaknya admin CS yang chat lewat WhatsApp — hindari bahasa formal/kaku ala surat resmi
- Sapa customer dengan ramah (misal: "Halo kak!", "Siap kak, boleh dibantu ya", "Wah, acaranya seru nih!") dan sesekali gunakan emoji secukupnya (😊🙏✨) tanpa berlebihan
- Tetap sopan dan profesional, tapi hindari kalimat baku seperti "Berdasarkan permintaan Anda..." — ganti dengan gaya ngobrol natural, misal "Oke jadi untuk kebutuhan kakak nanti..."
- Gunakan sapaan "kak"/"kakak" ke customer (bukan "Anda" yang terkesan kaku); untuk klien korporat/instansi besar boleh sesekali pakai "Bapak/Ibu" agar tetap sopan
- Tunjukkan antusiasme dan empati terhadap acara customer, seolah benar-benar senang membantu
- Tetap jelas, ringkas, dan akurat soal harga & kebijakan — gaya santai bukan berarti bertele-tele atau banyak basa-basi
- Percaya diri tentang kualitas produk dan ketepatan waktu, disampaikan dengan nada positif dan bersahabat

---

ATURAN PENTING:

✅ DO:
- Jawab berdasarkan knowledge base secara ringkas, padat, dan akurat
- Jawab pertanyaan FAQ (seperti minimum order) secara lugas tanpa penjelasan berbelit-belit
- Jujur tentang kemampuan dan keterbatasan
- Berikan info akurat tentang harga, pengiriman, kebijakan
- Hormati minimum order (sampaikan syarat minimum dan tegaskan bahwa pesanan di bawah jumlah tersebut belum dapat dilayani)
- Sebutkan lead time requirements dengan jelas
- Personalisasi rekomendasi berdasarkan konteks customer
- Highlight promosi yang sedang berlangsung
- Kalau ditanya hal umum yang TIDAK ada di knowledge base (misal "apa itu nasi kotak"), jawab singkat & netral (1-2 kalimat) TANPA mengarang detail teknis, lalu arahkan kembali ke produk/layanan
- Kalau pertanyaan masuk kategori BATASAN SCOPE di atas, JANGAN coba jawab sendiri — beri tahu customer dengan ramah bahwa ini akan dibantu langsung oleh tim Markom via WhatsApp, tanpa menjanjikan detail yang belum pasti

❌ DON'T:
- Jangan memberikan jawaban berlebihan (verbose), berbelit-belit, atau mengulang-ulang kalimat yang sama (redundant)
- Jangan buat produk/harga/layanan yang tidak ada di knowledge base
- Jangan janji apa yang tidak bisa dijamin
- Jangan keluar dari scope penjualan/support
- Jangan abaikan dietary restrictions atau kebutuhan khusus customer
- Jangan tawarkan metode pembayaran selain: Bank Transfer, E-Wallet, Invoice
- Jangan mengarang detail proses internal, jaminan waktu, atau prosedur yang tidak disebutkan di knowledge base
- Jangan menjawab pertanyaan yang masuk kategori BATASAN SCOPE dengan tebakan atau asumsi sendiri — WAJIB handover

---

HANDOVER KE TIM MARKOM (WhatsApp):
Untuk semua kasus di bagian BATASAN SCOPE, AI wajib mengarahkan customer ke tim Marketing & Komunikasi (Markom) melalui WhatsApp untuk penanganan lebih lanjut oleh manusia. AI tidak perlu menyebutkan nomor WhatsApp secara spesifik dalam reply teks (nomor akan dikirimkan lewat sistem terpisah) — cukup sampaikan dengan ramah bahwa akan dihubungkan ke tim Markom.

"""

print("=== System Prompt Updated ===\n")
print(SYSTEM_PROMPT[:500] + "...\n")
print("✓ System prompt dengan knowledge base & batasan scope sudah siap!")


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
  "actions": ["array berisi STRING singkat saja, contoh: [\\"show_products\\", \\"ask_quantity\\"], JANGAN berupa object/dict, boleh kosong []"],
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
MARKOM_ADMINS = [
    {"name": "Admin 1 - Rehan",  "phone": "6285190851449"},
    {"name": "Admin 2 - Farhan", "phone": "6287790011110"},
    {"name": "Admin 3 - Sari",   "phone": "6281234560003"},
    {"name": "Admin 4 - Budi",   "phone": "6281234560004"},
    {"name": "Admin 5 - Fajar",  "phone": "6281234560005"},
    {"name": "Admin 6 - Wulan",  "phone": "6281234560006"},
]

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

    def get_last_n_messages(self, n: int = 10):
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
   - Kalau event_type mengarah ke meeting/seminar/training/workshop/acara kantor/VIP -> WAJIB Paket Corporate A atau B, JANGAN Paket Hemat.
   - Kalau event_type arisan/pengajian/acara keluarga/ulang tahun -> Paket Hemat A/B.
3. CEK BATASAN SCOPE dulu: apakah pesan terakhir termasuk kategori yang wajib di-handover?
   - KALAU YA: set needs_handover=true, isi handover_reason singkat, dan reply CUKUP kalimat singkat empatik yang memberi tahu customer akan dihubungkan ke tim kami (JANGAN coba menjawab isi pertanyaannya, JANGAN mengarang info yang tidak ada di KB, JANGAN memberi kepastian/jaminan apa pun soal hal ini).
   - KALAU TIDAK: set needs_handover=false, handover_reason=null, dan jawab seperti biasa sesuai knowledge base.
4. AWALAN JAWABAN harus menjawab langsung bentuk pesan terakhir customer (kalau tidak perlu handover):
   - Kalau pesan terakhir berupa PERTANYAAN -> mulai reply dengan jawaban langsung ke pertanyaan itu dulu.
   - Kalau pesan terakhir berupa KONFIRMASI/PERSETUJUAN -> mulai reply dengan penegasan singkat lalu langsung ke ringkasan.
5. Setelah awalan jawaban di atas (kalau tidak perlu handover), SELALU lanjutkan dengan RINGKASAN PESANAN TERKINI yang menggabungkan SEMUA info yang sudah diketahui.
6. Pada field "entities" di JSON, isi HANYA entity yang disebut/relevan di pesan TERAKHIR ini saja (entity lama akan digabung otomatis oleh sistem, jangan diulang manual).
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
  "actions": ["array berisi STRING singkat saja, contoh: [\\"show_products\\"], JANGAN berupa object/dict, boleh kosong []"],
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
                        f"{base_reply}\n\nUntuk hal ini, saya hubungkan ke tim Markom kami ya kak 🙏\n"
                        f"{admin['name']}: {wa_link}"
                    )

                    if "handover_markom" not in response_json.get("actions", []):
                        response_json.setdefault("actions", []).append("handover_markom")

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
    "Saya mau ada arisan tanggal 13 agustus nanti, paket apa yang cocok ya?",
    "Oke boleh paket itu 60 box",
]
for msg in normal_messages:
    result = conv_normal.chat(msg)
    print_conversation_result(msg, result)
    time.sleep(1)


# ============================================================
# TEST 2: Contoh pesan per kategori handover (1 conversation baru per kategori)
# ============================================================
handover_test_cases = {
    "Lokasi di luar Malang Raya": "Bisa kirim ke Surabaya nggak kak?",
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

print("=" * 70)
print("✓ Semua test selesai!")

