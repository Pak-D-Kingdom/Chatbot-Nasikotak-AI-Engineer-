import os
from dotenv import load_dotenv

load_dotenv()

# === LLM Provider (9router) ===
NINEROUTER_API_KEY = os.getenv("NINEROUTER_API_KEY")
NINEROUTER_BASE_URL = os.getenv("NINEROUTER_BASE_URL", "http://localhost:20128/v1")
LLM_MODEL = "nasikotak"
LLM_MAX_TOKENS = 512
LLM_TEMPERATURE = 0.1
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
        if "|" in pair:
            name, phone = pair.split("|", 1)
            MARKOM_ADMINS.append({"name": name.strip(), "phone": phone.strip()})
if not MARKOM_ADMINS:
    MARKOM_ADMINS = [{"name": "Admin Default", "phone": "628000000000"}]

# === RAG ===
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
RAG_TOP_K = 6
RAG_MAX_CONTEXT_TOKENS = 3000

# === Conversation ===
MAX_CONVERSATION_HISTORY = 10
