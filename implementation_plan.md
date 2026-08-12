# AI Sales Chatbot — Implementation Plan (AI Engineer Division)

Berdasarkan [PRODUCT REQUIREMENT DOCUMENT (PRD).md](file:///E:/Maganghub/Projek 1/PRODUCT REQUIREMENT DOCUMENT (PRD).md), berikut adalah rencana implementasi untuk membangun **AI Pipeline** (LLM + RAG + Sales Engine) dalam format **Jupyter Notebook**.

> [!NOTE]
> Scope divisi: **AI Engineer** — fokus pada AI pipeline, bukan full website. Deliverable utama berupa **notebook** yang mendemonstrasikan seluruh kemampuan AI, serta **module Python** yang siap diintegrasikan oleh tim lain (frontend/backend).

---

## Prerequisites — Conda Environment

> [!IMPORTANT]
> Project ini menggunakan **Miniconda** dengan environment `nasikotak` (Python 3.11). **Selalu aktifkan environment terlebih dahulu** sebelum menjalankan command apapun:

```bash
conda activate nasikotak
```

| Item | Detail |
|------|--------|
| **Environment Name** | `nasikotak` |
| **Python Version** | 3.11.15 |
| **Package Manager** | Miniconda |
| **Workspace** | `E:\Maganghub\Projek 1` |

Instalasi dependencies:
```bash
conda activate nasikotak
pip install -r requirements.txt
```

---

## Catatan Review & Perbaikan PRD

> [!IMPORTANT]
> Beberapa hal yang saya perbaiki, tambahkan, atau perlu diperhatikan dari PRD:

### Perbaikan & Tambahan

1. **Upselling Logic tidak cukup spesifik** — PRD menyebutkan upselling tapi tidak mendefinisikan threshold kapan upselling di-trigger. Saya tambahkan logic: upselling aktif jika ada paket dengan harga ≤ 120% dari budget customer dan memiliki value lebih baik.

2. **Cross-Selling (FR-11) tidak memiliki data pendukung** — PRD menyebutkan cross-selling untuk snack box/minuman tapi knowledge base structure tidak menyertakan produk tambahan ini. Saya tambahkan `addons/` folder di knowledge base.

3. **Rate Limiting belum detail** — PRD hanya menyebut "rate limiting sederhana" tanpa spesifikasi. Saya tambahkan: max 30 requests/menit per session, max 5 requests/detik global.

4. **Session Management belum didefinisikan** — PRD menggunakan `session_id` tapi tidak menjelaskan bagaimana session dibuat/dikelola. Saya tambahkan UUID-based session dengan expiry 24 jam.

5. **Conversation Memory hanya in-session** — PRD menyebut menyimpan context tapi tidak jelaskan persistensi. Untuk MVP: simpan di SQLite per session, auto-expire 24 jam.

6. **Embedding Model Size** — Menggunakan **multilingual-e5-small** (~470MB, 384 dimensi) sebagai pilihan yang ringan namun tetap akurat untuk Bahasa Indonesia. Jauh lebih efisien dibanding BGE-M3 (~2.3GB) dengan trade-off minimal pada knowledge base skala kecil.

7. **Structured Output dari Gemini** — PRD sudah benar menggunakan structured output, tapi perlu ditambahkan JSON Schema definition yang eksplisit untuk setiap tipe response.

8. **WhatsApp CTA Link Format** — PRD tidak menjelaskan format WhatsApp link. Saya tambahkan template: `https://wa.me/{phone}?text={encoded_message}` dengan pre-filled order summary.

---

## User Review Required

> [!WARNING]
> **Keputusan teknis yang perlu persetujuan:**

1. **Embedding Model**: ~~BGE-M3~~ → Menggunakan **`intfloat/multilingual-e5-small`** (~470MB, 384 dimensi). Ringan, multilingual (termasuk Bahasa Indonesia), performa sangat memadai untuk knowledge base skala kecil. ✅ Disetujui.

2. **Data Produk Riil**: Apakah sudah ada data produk nasi kotak yang riil (nama paket, harga, menu), atau saya perlu membuat data dummy yang realistis?

3. **Gemini API Key**: Sudah tersedia atau perlu didaftarkan dulu?

4. **Nomor WhatsApp Admin**: Diperlukan untuk WhatsApp CTA message template. Bisa menggunakan placeholder dulu?

---

## Open Questions

> [!NOTE]
> Pertanyaan klarifikasi yang **tidak** memblokir development (bisa menggunakan default):

1. **Bahasa** — Apakah chatbot hanya Bahasa Indonesia, atau perlu support bilingual? (Default: Bahasa Indonesia only)
2. **Max conversation history** — Berapa pesan terakhir yang dikirim ke LLM? (Default: 20 pesan terakhir)
3. **Apakah ada tim backend/frontend** yang akan mengintegrasikan output notebook ini ke FastAPI + React? (Default: siapkan module Python yang modular & siap dipanggil)

---

## Project Structure

```text
Projek 1/
├── notebooks/
│   ├── 01_setup_and_data.ipynb           # Setup, seed data, knowledge base
│   ├── 02_llm_integration.ipynb          # Gemini integration & prompt engineering
│   ├── 03_rag_pipeline.ipynb             # RAG: embedding, FAISS, retrieval
│   ├── 04_sales_engine.ipynb             # Sales logic, intent, recommendation
│   └── 05_full_pipeline.ipynb            # Full pipeline demo & testing
│
├── src/                                  # Reusable Python modules
│   ├── __init__.py
│   ├── config.py                         # Settings & env vars
│   ├── database.py                       # SQLite setup & models
│   ├── llm_service.py                    # Gemini client
│   ├── rag_service.py                    # RAG pipeline
│   ├── sales_engine.py                   # Sales logic & recommendation
│   ├── lead_manager.py                   # Lead collection
│   ├── conversation_manager.py           # Session & memory
│   └── prompt_templates.py               # System prompts
│
├── knowledge_base/
│   ├── products/
│   │   ├── paket_hemat_a.md
│   │   ├── paket_hemat_b.md
│   │   ├── paket_corporate_a.md
│   │   └── paket_corporate_b.md
│   ├── faq/
│   │   ├── ordering.md
│   │   ├── payment.md
│   │   └── custom_menu.md
│   ├── promotion/
│   │   └── current_promotion.md
│   ├── delivery/
│   │   └── delivery_area.md
│   ├── addons/
│   │   ├── snack_box.md
│   │   └── beverages.md
│   └── company/
│       └── company_profile.md
│
├── faiss_index/                          # Generated FAISS index
│   ├── index.faiss
│   └── metadata.json
│
├── data/
│   └── nasikotak.db                      # SQLite database
│
├── tests/
│   └── test_scenarios.py                 # 25+ test cases
│
├── .env                                  # API keys (gitignored)
├── .env.example
├── requirements.txt
├── PRODUCT REQUIREMENT DOCUMENT (PRD).md
└── README.md
```

---

## Proposed Changes

### Component 1: Environment & Dependencies

#### [NEW] [requirements.txt](file:///E:/Maganghub/Projek 1/requirements.txt)
```text
# Core
google-genai>=1.0
sentence-transformers>=3.0
faiss-cpu>=1.8
sqlalchemy>=2.0

# Utilities
python-dotenv>=1.0
pydantic>=2.0

# Notebook
jupyter
ipywidgets

# Testing
pytest
```

#### [NEW] [.env.example](file:///E:/Maganghub/Projek 1/.env.example)
```text
GEMINI_API_KEY=your_api_key_here
WHATSAPP_NUMBER=6281234567890
```

---

### Component 2: Knowledge Base (12 files)

Setiap file mengandung structured markdown + YAML frontmatter metadata:

```yaml
---
document_id: P001
type: product
category: hemat
price: 20000
minimum_order: 20
event_types: [arisan, pengajian, acara_keluarga]
active: true
---
# Paket Hemat A
Harga: Rp18.000/box
...
```

#### [NEW] Knowledge Base Files
| File | Konten |
|------|--------|
| `products/paket_hemat_a.md` | Paket budget-friendly, Rp18.000/box |
| `products/paket_hemat_b.md` | Paket hemat upgraded, Rp23.000/box |
| `products/paket_corporate_a.md` | Paket corporate standard, Rp27.000/box |
| `products/paket_corporate_b.md` | Paket corporate premium, Rp33.000/box |
| `faq/ordering.md` | Cara pemesanan, min order, lead time |
| `faq/payment.md` | Metode pembayaran, DP, full payment |
| `faq/custom_menu.md` | Ketentuan custom menu |
| `promotion/current_promotion.md` | Promo aktif |
| `delivery/delivery_area.md` | Area pengiriman & biaya |
| `addons/snack_box.md` | Snack box options |
| `addons/beverages.md` | Pilihan minuman |
| `company/company_profile.md` | Profil perusahaan |

---

### Component 3: Database & Seed Data

#### [NEW] [database.py](file:///E:/Maganghub/Projek 1/src/database.py)
- SQLAlchemy engine dengan SQLite (`data/nasikotak.db`)
- Table definitions sesuai PRD Section 32:
  - `products` — nama, harga, kategori, menu, minimum_order, dll.
  - `promotions` — nama, tipe diskon, value, periode, conditions
  - `leads` — nama, phone, quantity, budget, event, product_id, intent, status
  - `conversations` — session_id, sender, message, intent, purchase_intent
- Auto-create tables

#### Notebook coverage: `01_setup_and_data.ipynb`

---

### Component 4: LLM Integration (Gemini)

#### [NEW] [llm_service.py](file:///E:/Maganghub/Projek 1/src/llm_service.py)
- Gemini client initialization menggunakan `google-genai` SDK
- Model: `gemini-2.5-flash` (atau `gemini-2.5-flash-lite`)
- System prompt sesuai PRD Section 35
- **Structured output** menggunakan Gemini's JSON mode:
  ```python
  {
      "reply": str,           # Natural language response
      "intent": str,          # product_inquiry, recommendation, order, etc.
      "purchase_intent": str, # low, medium, high, ready_to_order
      "entities": {
          "quantity": int | None,
          "budget_per_box": int | None,
          "event_type": str | None,
          "location": str | None,
          "event_date": str | None,
          "customer_name": str | None,
          "customer_phone": str | None
      },
      "actions": list[str]    # show_products, collect_lead, whatsapp_cta, human_handoff
  }
  ```
- Conversation history management (max 20 pesan terakhir)
- Error handling & retry logic (max 3 retries)

#### [NEW] [prompt_templates.py](file:///E:/Maganghub/Projek 1/src/prompt_templates.py)
- System prompt lengkap (role, behavior, rules, sales strategy, upselling, CTA)
- Context injection template (RAG results → prompt)
- Few-shot examples untuk structured output
- Anti-hallucination instructions

#### Notebook coverage: `02_llm_integration.ipynb`
Isi notebook:
1. Setup Gemini client
2. Test basic chat
3. Test structured output
4. Test system prompt behavior
5. Test conversation history
6. Test anti-hallucination
7. Test berbagai variasi bahasa Indonesia

---

### Component 5: RAG Engine

#### [NEW] [rag_service.py](file:///E:/Maganghub/Projek 1/src/rag_service.py)
- **Document Loader**: Load semua `.md` files dari `knowledge_base/`
- **Chunking Strategy**:
  - Chunk by markdown sections (header-based splitting)
  - Chunk size: ~500 tokens, overlap: 50 tokens
- **Embedding**: multilingual-e5-small via `sentence-transformers`
  - Model: `intfloat/multilingual-e5-small`
  - Dimensi: 384
  - Size: ~470MB (vs BGE-M3 ~2.3GB)
- **FAISS Index**:
  - `IndexFlatIP` (inner product) untuk cosine similarity
  - Save/load index ke disk (`faiss_index/`)
- **Retrieval**:
  - Top-K: 5 documents
  - Metadata filtering (category, price range, event type)
  - Re-ranking berdasarkan relevance score
- **Context Construction**:
  - Format retrieved docs menjadi structured context
  - Inject ke system prompt sebelum dikirim ke Gemini

#### Notebook coverage: `03_rag_pipeline.ipynb`
Isi notebook:
1. Load & parse knowledge base documents
2. Chunking demonstration
3. Generate embeddings (multilingual-e5-small)
4. Build FAISS index
5. Test semantic search dengan berbagai query
6. Metadata filtering demo
7. Context construction → Gemini
8. Compare: dengan RAG vs tanpa RAG (hallucination test)

---

### Component 6: Sales Intelligence Engine

#### [NEW] [sales_engine.py](file:///E:/Maganghub/Projek 1/src/sales_engine.py)
- **Intent Classification** (dari Gemini structured output):
  - `greeting`, `product_inquiry`, `product_recommendation`, `price_calculation`
  - `order_intent`, `promotion_inquiry`, `delivery_inquiry`
  - `complaint`, `human_request`, `other`

- **Purchase Intent Detection** (sesuai PRD Section 17):
  - `LOW` → Eksplorasi ("Ada paket apa?")
  - `MEDIUM` → Membandingkan ("Kalau 100 box berapa?")
  - `HIGH` → Tertarik ("Saya tertarik paket B")
  - `READY_TO_ORDER` → Siap beli ("Saya pesan 100 box")

- **Product Recommendation Logic**:
  ```python
  def recommend(budget, quantity, event_type):
      # 1. Filter products by budget (price <= budget)
      # 2. Filter by minimum_order (min_order <= quantity)
      # 3. Score by event_type suitability
      # 4. Sort by relevance score
      # 5. Return top 3 recommendations
  ```

- **Price Calculation** (backend-computed, NOT LLM):
  ```python
  total = price_per_box * quantity
  # Apply promotions if eligible
  ```

- **Upselling Logic**:
  ```python
  def check_upsell(selected_product, budget):
      # Find products with price <= budget * 1.2
      # that have better menu/features
      # Return upsell suggestion with price difference
  ```

#### [NEW] [conversation_manager.py](file:///E:/Maganghub/Projek 1/src/conversation_manager.py)
- Session-based conversation state:
  ```python
  session_context = {
      "session_id": "uuid",
      "quantity": None,
      "budget_per_box": None,
      "event_type": None,
      "location": None,
      "event_date": None,
      "selected_product": None,
      "customer_name": None,
      "customer_phone": None,
      "purchase_intent": "low",
      "messages": []
  }
  ```
- Update context incrementally dari setiap pesan
- Persist ke SQLite

#### Notebook coverage: `04_sales_engine.ipynb`
Isi notebook:
1. Intent classification demo
2. Entity extraction: budget, quantity, event
3. Product recommendation berdasarkan filter
4. Price calculation demo
5. Upselling logic demo
6. Cross-selling demo
7. Purchase intent tracking (LOW → MEDIUM → HIGH → READY)
8. Conversation context accumulation (multi-turn demo)

---

### Component 7: Lead Management

#### [NEW] [lead_manager.py](file:///E:/Maganghub/Projek 1/src/lead_manager.py)
- **Lead Extraction**: Trigger ketika purchase_intent = `HIGH` atau `READY_TO_ORDER`
- **Lead Data Collection**:
  - Nama, Phone/WhatsApp (dari conversation)
  - Quantity, Budget, Event, Date, Location (dari session context)
  - Selected product, Notes (auto-generated summary)
- **Lead Saving**: Insert ke SQLite `leads` table
- **WhatsApp Message Template**:
  ```python
  def generate_whatsapp_link(lead):
      message = f"""Halo Admin, saya ingin memesan:
      Paket: {lead.product_name}
      Jumlah: {lead.quantity} box
      Acara: {lead.event_type}
      Tanggal: {lead.event_date}
      Lokasi: {lead.location}
      Estimasi: Rp{lead.total_price:,}
      Nama: {lead.name}"""
      return f"https://wa.me/{phone}?text={quote(message)}"
  ```

#### Notebook coverage: `05_full_pipeline.ipynb`

---

### Component 8: Full Pipeline Demo (Notebook 05)

#### [NEW] [05_full_pipeline.ipynb](file:///E:/Maganghub/Projek 1/notebooks/05_full_pipeline.ipynb)

Notebook utama yang mendemonstrasikan **seluruh pipeline end-to-end**:

**Section 1 — Interactive Chat Loop**
```python
def chat(user_message, session_id=None):
    """
    Full pipeline:
    1. Load/create session
    2. RAG retrieval
    3. Build prompt (system + context + history + message)
    4. Call Gemini → structured output
    5. Run sales engine (recommendation, price calc, upsell)
    6. Update session context
    7. Check lead trigger
    8. Return response
    """
```

**Section 2 — Sales Scenario Simulations**
- Scenario A: Customer individu, budget rendah, arisan
- Scenario B: Corporate customer, 100 box meeting
- Scenario C: Event organizer, custom menu → human handoff
- Scenario D: Customer bertanya produk yang tidak ada → anti-hallucination

**Section 3 — 28 Test Cases**
Seluruh test case dari PRD Section 42 dijalankan dan divalidasi.

**Section 4 — Lead Report**
- Query semua leads yang terkumpul
- Tampilkan dalam tabel
- Generate WhatsApp link untuk setiap lead

**Section 5 — Metrics Dashboard (Sederhana)**
- Total conversations
- Intent distribution (pie chart)
- Purchase intent funnel
- Lead conversion rate
- Unanswered question rate

---

## Notebooks Detail

### Notebook 01: Setup & Data
| Section | Konten |
|---------|--------|
| 1.1 | Install & import dependencies |
| 1.2 | Setup `.env` dan konfigurasi |
| 1.3 | Inisialisasi SQLite database |
| 1.4 | Seed product data (4 paket) |
| 1.5 | Seed promotion data |
| 1.6 | Seed delivery area data |
| 1.7 | Create knowledge base markdown files |
| 1.8 | Verifikasi: query DB, list knowledge base |

### Notebook 02: LLM Integration
| Section | Konten |
|---------|--------|
| 2.1 | Setup Gemini client |
| 2.2 | Basic chat test |
| 2.3 | System prompt implementation |
| 2.4 | Structured output (JSON mode) |
| 2.5 | Conversation history handling |
| 2.6 | Error handling & retry |
| 2.7 | Anti-hallucination test |
| 2.8 | Variasi bahasa Indonesia test |

### Notebook 03: RAG Pipeline
| Section | Konten |
|---------|--------|
| 3.1 | Document loading & parsing |
| 3.2 | Chunking strategy |
| 3.3 | multilingual-e5-small embedding generation |
| 3.4 | FAISS index building |
| 3.5 | Semantic search testing |
| 3.6 | Metadata filtering |
| 3.7 | Context construction |
| 3.8 | RAG + Gemini integration test |
| 3.9 | Perbandingan: dengan RAG vs tanpa RAG |

### Notebook 04: Sales Intelligence
| Section | Konten |
|---------|--------|
| 4.1 | Intent classification demo |
| 4.2 | Budget detection (variasi bahasa) |
| 4.3 | Quantity detection |
| 4.4 | Event type detection |
| 4.5 | Product recommendation engine |
| 4.6 | Price calculation (backend-computed) |
| 4.7 | Upselling logic |
| 4.8 | Cross-selling logic |
| 4.9 | Purchase intent tracking |
| 4.10 | Multi-turn conversation demo |

### Notebook 05: Full Pipeline & Testing
| Section | Konten |
|---------|--------|
| 5.1 | Full pipeline function `chat()` |
| 5.2 | Interactive chat loop (input-based) |
| 5.3 | Scenario A: Individual customer |
| 5.4 | Scenario B: Corporate customer |
| 5.5 | Scenario C: Human handoff |
| 5.6 | Scenario D: Anti-hallucination |
| 5.7 | 28 test cases execution |
| 5.8 | Lead report & WhatsApp links |
| 5.9 | Simple metrics dashboard |

---

## Test Cases (28 Cases)

| # | Kategori | Input | Expected Behavior |
|---|----------|-------|-------------------|
| 1 | Product | "Berapa harga Paket A?" | Return harga dari DB, bukan LLM |
| 2 | Product | "Menu paket corporate B apa?" | Return menu dari knowledge base |
| 3 | Budget | "Budget 25 ribu" | Extract budget_per_box = 25000 |
| 4 | Budget | "Sekitar 30k per box" | Extract budget_per_box = 30000 |
| 5 | Quantity | "Saya butuh 100 box" | Extract quantity = 100 |
| 6 | Quantity | "Untuk 50 orang" | Extract quantity = 50 |
| 7 | Event | "Untuk meeting kantor" | Extract event_type = "meeting" |
| 8 | Event | "Acara pengajian" | Extract event_type = "pengajian" |
| 9 | Combined | "100 box meeting budget 30 ribu" | Extract all entities |
| 10 | Recommendation | "Rekomendasikan paket" | Return products from DB |
| 11 | Comparison | "Bedanya paket A dan B?" | Compare from knowledge base |
| 12 | Cheapest | "Yang paling murah?" | Return lowest price product |
| 13 | Premium | "Ada yang lebih premium?" | Upsell to higher tier |
| 14 | Promotion | "Ada promo?" | Return from knowledge base |
| 15 | Delivery | "Bisa kirim ke Malang?" | Check delivery area |
| 16 | Order | "Saya mau pesan" | Trigger lead collection |
| 17 | Custom | "Bisa custom menu?" | Redirect to human/admin |
| 18 | Human | "Mau bicara admin" | Trigger human handoff |
| 19 | Hallucination | "Ada sushi box?" | "Informasi tidak tersedia" |
| 20 | Hallucination | "Harga pizza?" | "Informasi tidak tersedia" |
| 21 | Calculation | "100 box paket A berapa total?" | Backend-calculated total |
| 22 | Intent LOW | "Ada paket apa?" | purchase_intent = low |
| 23 | Intent HIGH | "Tertarik paket B" | purchase_intent = high |
| 24 | Intent READY | "Pesan 100 box sekarang" | purchase_intent = ready_to_order |
| 25 | Lead | Provide name + phone | Save lead to DB |
| 26 | WhatsApp | After lead collected | Generate WhatsApp CTA link |
| 27 | Memory | Multi-turn: qty → budget → event | Accumulate context correctly |
| 28 | Error | API timeout/error | Friendly error message |

---

## Timeline (7 Hari)

### Day 1 — Project Setup & Business Data
| Task | Detail |
|------|--------|
| Setup conda env & dependencies | `pip install -r requirements.txt` |
| Setup project structure | `src/`, `notebooks/`, `knowledge_base/` |
| Create SQLite database & models | `src/database.py` |
| Create knowledge base (12 files) | Markdown + metadata |
| Seed database | Product, promotion, delivery data |
| **Notebook 01** | Complete & tested |

**Acceptance**: DB seeded, knowledge base siap, semua bisa di-query.

---

### Day 2 — LLM Integration (Gemini)
| Task | Detail |
|------|--------|
| Gemini API setup | `src/llm_service.py` |
| System prompt engineering | `src/prompt_templates.py` |
| Structured output (JSON mode) | Intent, entities, actions |
| Conversation history | In-memory + SQLite |
| Error handling | Retry, timeout, fallback |
| **Notebook 02** | Complete & tested |

**Acceptance**: Bisa kirim pesan ke Gemini, dapat structured response.

---

### Day 3 — RAG Pipeline
| Task | Detail |
|------|--------|
| Document loader & parser | `src/rag_service.py` |
| multilingual-e5-small embedding | sentence-transformers |
| FAISS index build & save | `faiss_index/` |
| Semantic search + metadata filter | Top-5 retrieval |
| Context injection ke Gemini | RAG + LLM integration |
| **Notebook 03** | Complete & tested |

**Acceptance**: AI menjawab berdasarkan knowledge base. Hallucination test passed.

---

### Day 4 — Sales Intelligence Engine
| Task | Detail |
|------|--------|
| Intent classification | Via Gemini structured output |
| Entity extraction | Budget, quantity, event, location |
| Product recommendation | Filter + scoring |
| Price calculation | Backend-computed |
| Upselling & cross-selling | Threshold-based |
| Purchase intent tracking | LOW → MEDIUM → HIGH → READY |
| **Notebook 04** | Complete & tested |

**Acceptance**: AI bisa rekomendasi paket berdasarkan kebutuhan customer.

---

### Day 5 — Lead Generation & Full Pipeline
| Task | Detail |
|------|--------|
| Lead extraction & saving | `src/lead_manager.py` |
| WhatsApp message template | Pre-filled link generation |
| Conversation manager | `src/conversation_manager.py` |
| Full `chat()` pipeline function | End-to-end |
| **Notebook 05** (Section 1-4) | Interactive demo |

**Acceptance**: Full pipeline berjalan end-to-end. Lead tersimpan.

---

### Day 6 — Testing & Validation
| Task | Detail |
|------|--------|
| 28 test cases | Automated di notebook |
| Hallucination testing | Verify anti-hallucination |
| Sales scenario simulation | 4 skenario lengkap |
| Edge case testing | Invalid input, empty responses |
| Performance measurement | Response time logging |
| **Notebook 05** (Section 5-9) | Metrics & report |

**Acceptance**: Semua 28 test cases passed. Metrics terdokumentasi.

---

### Day 7 — Documentation & Finalization
| Task | Detail |
|------|--------|
| Code cleanup & refactoring | Clean `src/` modules |
| README.md | Setup guide, architecture, usage |
| Notebook cleanup | Clear outputs, add markdown explanations |
| `test_scenarios.py` | Pytest version of test cases |
| Final demo run | Record/screenshot full pipeline |

**Acceptance**: Semua deliverables siap. Module Python siap diintegrasikan.

---

## Deliverables

| # | Deliverable | Format |
|---|-------------|--------|
| 1 | Notebook 01: Setup & Data | `.ipynb` |
| 2 | Notebook 02: LLM Integration | `.ipynb` |
| 3 | Notebook 03: RAG Pipeline | `.ipynb` |
| 4 | Notebook 04: Sales Engine | `.ipynb` |
| 5 | Notebook 05: Full Pipeline & Testing | `.ipynb` |
| 6 | Python modules (`src/`) | `.py` — siap integrasi |
| 7 | Knowledge base | Markdown files |
| 8 | FAISS index | Binary + metadata |
| 9 | SQLite database | Seeded & tested |
| 10 | README.md | Documentation |

---

## Verification Plan

### Automated Tests
```bash
conda activate nasikotak
python -m pytest tests/test_scenarios.py -v
```

### Notebook Verification
Setiap notebook dijalankan dari awal sampai akhir tanpa error. Output dicek secara manual untuk:
1. **Akurasi harga** — Harga berasal dari DB, bukan LLM
2. **Anti-hallucination** — Bot tidak mengarang produk/promo
3. **Entity extraction** — Budget, quantity, event terdeteksi benar
4. **Recommendation relevance** — Paket sesuai kebutuhan
5. **Lead completeness** — Data lead lengkap tersimpan di DB
6. **WhatsApp link** — Link valid dengan pre-filled message
7. **Multi-turn memory** — Context terakumulasi benar
8. **Error handling** — Pesan error ramah saat API gagal
