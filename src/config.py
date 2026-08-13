import os
from dotenv import load_dotenv

load_dotenv()

# === LLM Provider ===
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.1-8b-instant"
LLM_MAX_TOKENS = 1500
LLM_TEMPERATURE = 0.2
LLM_MAX_RETRIES = 3

# === Paths ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = f"sqlite:///{os.path.join(PROJECT_ROOT, 'data', 'nasikotak.db')}"
KNOWLEDGE_BASE_DIR = os.path.join(PROJECT_ROOT, "knowledge_base")
FAISS_INDEX_DIR = os.path.join(PROJECT_ROOT, "faiss_index")

# === WhatsApp / Order ===
ORDER_WEB_URL = os.getenv("ORDER_WEB_URL", "https://ayambakarpakd.com/order")

# === Markom Admins (round-robin) ===
_admin_env = os.getenv("MARKOM_ADMINS", "")
MARKOM_ADMINS = []
if _admin_env:
    for pair in _admin_env.split(","):
        if ":" in pair:
            name, phone = pair.split(":", 1)
            MARKOM_ADMINS.append({"name": name.strip(), "phone": phone.strip()})
if not MARKOM_ADMINS:
    MARKOM_ADMINS = [{"name": "Admin Default", "phone": "628000000000"}]

# === RAG ===
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RAG_TOP_K = 5

# === Conversation ===
MAX_CONVERSATION_HISTORY = 20
