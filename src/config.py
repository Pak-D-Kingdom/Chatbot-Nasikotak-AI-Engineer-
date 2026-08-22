import os
import re
from dotenv import load_dotenv

# === Paths ===
# config.py berada di dalam folder src/, sedangkan .env ada di root project
# (sejajar dengan app.py). Makanya PROJECT_ROOT harus naik satu level lagi.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env dengan path eksplisit supaya tidak bergantung pada current
# working directory saat aplikasi dijalankan (root cause umum kenapa
# env var "hilang" padahal sudah diisi di file .env).
DOTENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(dotenv_path=DOTENV_PATH)

# === LLM Provider ===
LLM_API_KEY = os.getenv("NINEROUTER_API_KEY", "dummy-key-for-9router")
LLM_MODEL = "nasikotak"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:20128/v1")
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.2
LLM_MAX_RETRIES = 3

# === Paths (lanjutan) ===
DB_PATH = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', 'nasikotak.db')}"
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
FAISS_INDEX_DIR = os.path.join(PROJECT_ROOT, "faiss_index")

# === WhatsApp / Order ===
ORDER_WEB_URL = os.getenv("ORDER_WEB_URL", "https://ayambakarpakd.com/order")

# === Markom Admins (round-robin) ===
# Format yang diharapkan di .env:
#   MARKOM_ADMINS=Nama 1|62812xxxx,Nama 2|62813xxxx,...
_PHONE_PATTERN = re.compile(r'^\d{8,15}$')  # nomor tanpa "+" / spasi, 8-15 digit

def _parse_markom_admins(raw_value: str) -> list:
    """Parse MARKOM_ADMINS dari env string. Skip entry yang formatnya rusak
    (jangan sampai satu entry salah bikin semua admin hilang)."""
    admins = []
    if not raw_value:
        return admins

    for raw_pair in raw_value.split(","):
        pair = raw_pair.strip()
        if not pair:
            continue
        if "|" not in pair:
            print(f"[WARNING] MARKOM_ADMINS entry dilewati (tidak ada '|'): '{pair}'")
            continue

        name, phone = pair.split("|", 1)
        name = name.strip()
        phone = phone.strip()

        if not name or not phone:
            print(f"[WARNING] MARKOM_ADMINS entry dilewati (nama/nomor kosong): '{pair}'")
            continue

        if not _PHONE_PATTERN.match(phone):
            print(f"[WARNING] MARKOM_ADMINS entry dengan format nomor mencurigakan: '{pair}' "
                  f"(pastikan nomor internasional tanpa '+', contoh: 6281234567890)")
            # Tetap dimasukkan, hanya diberi warning, karena mungkin valid tapi pola beda.

        admins.append({"name": name, "phone": phone})

    return admins


_admin_env = os.getenv("MARKOM_ADMINS", "")
MARKOM_ADMINS = _parse_markom_admins(_admin_env)

if not MARKOM_ADMINS:
    print("[WARNING] MARKOM_ADMINS kosong atau gagal di-parse dari .env. "
          "Fallback ke Admin Default. Cek file .env di: " + DOTENV_PATH)
    MARKOM_ADMINS = [{"name": "Admin Default", "phone": "628000000000"}]
else:
    # Log aman: jangan cetak nomor penuh ke console/log produksi.
    masked = [f"{a['name']} ({a['phone'][:4]}xxxxx)" for a in MARKOM_ADMINS]
    print(f"[INFO] MARKOM_ADMINS berhasil dimuat ({len(MARKOM_ADMINS)} admin): {masked}")

# === RAG ===
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RAG_TOP_K = 6
RAG_MAX_CONTEXT_TOKENS = 3000

# === Conversation ===
MAX_CONVERSATION_HISTORY = 10