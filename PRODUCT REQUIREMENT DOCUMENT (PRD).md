# PRODUCT REQUIREMENT DOCUMENT (PRD)

## AI Sales Chatbot untuk Website Nasi Kotak

**Version:** 1.0 — MVP  
**Target Development:** 7 Hari  
**Platform:** Website Nasi Kotak  
**Primary Objective:** Meningkatkan engagement dan conversion calon pelanggan melalui AI Sales Assistant.

---

# 1. Executive Summary

AI Sales Chatbot adalah chatbot berbasis Large Language Model (LLM) yang ditempatkan pada website bisnis nasi kotak.

Chatbot dirancang bukan hanya sebagai FAQ chatbot, tetapi sebagai **AI Sales Assistant** yang dapat:

- Memahami kebutuhan calon pelanggan.
- Menanyakan kebutuhan yang belum diketahui.
- Mencari informasi produk dari knowledge base.
- Merekomendasikan paket nasi kotak.
- Menyesuaikan rekomendasi dengan budget dan jumlah pesanan.
- Menghitung estimasi total harga.
- Melakukan soft-selling dan upselling.
- Mendeteksi purchase intent.
- Mengumpulkan informasi calon pelanggan.
- Mengarahkan pelanggan ke WhatsApp atau proses pemesanan.

Sistem menggunakan pendekatan **LLM + RAG + Business Logic**, sehingga LLM tidak menjadi sumber kebenaran mengenai harga, menu, promo, atau aturan bisnis.

---

# 2. Background

Website bisnis nasi kotak pada umumnya berfungsi sebagai media informasi.

Calon pelanggan harus mencari sendiri informasi seperti:

- Harga paket.
- Isi menu.
- Paket yang cocok untuk acara tertentu.
- Minimum order.
- Area pengiriman.
- Promo.
- Estimasi biaya.

Hal ini dapat menyebabkan pelanggan meninggalkan website sebelum melakukan pemesanan.

AI Sales Chatbot akan mengubah website menjadi media interaksi penjualan yang memungkinkan pelanggan mendapatkan rekomendasi secara langsung melalui percakapan.

---

# 3. Problem Statement

### Problem 1 — Customer harus mencari informasi sendiri

Pelanggan harus membuka beberapa halaman untuk mengetahui paket, harga, menu, dan informasi lainnya.

### Problem 2 — Tidak semua pelanggan mengetahui paket yang sesuai

Customer sering hanya mengetahui:

> "Saya punya budget Rp25.000 dan butuh 100 box."

Tetapi tidak mengetahui paket mana yang cocok.

### Problem 3 — Customer service tidak selalu tersedia

Pelanggan yang mengunjungi website di luar jam kerja tidak mendapatkan respons langsung.

### Problem 4 — Website belum mengoptimalkan conversion

Website memberikan informasi, tetapi belum secara aktif membantu pelanggan mengambil keputusan pembelian.

---

# 4. Product Vision

> **Mengubah website nasi kotak menjadi AI-powered sales channel yang mampu membantu pelanggan menemukan produk yang tepat dan mengarahkan mereka hingga siap melakukan pemesanan.**

---

# 5. Product Goals

## Primary Goals

1. Meningkatkan engagement pengunjung website.
2. Membantu pelanggan menemukan paket yang sesuai.
3. Memberikan informasi produk secara cepat.
4. Meningkatkan purchase intent.
5. Menghasilkan qualified leads.
6. Mengarahkan pelanggan ke proses pemesanan.

## Secondary Goals

1. Mengurangi pertanyaan sederhana yang harus dijawab admin.
2. Menyediakan customer assistance 24/7.
3. Memberikan pengalaman pembelian yang lebih personal.

---

# 6. Success Metrics

MVP akan mengukur beberapa indikator:

### Chat Engagement Rate

Jumlah visitor yang menggunakan chatbot dibandingkan total visitor.

### Lead Conversion Rate

```text
Jumlah lead
────────────── × 100%
Jumlah pengguna chatbot
```

### Purchase Intent Rate

Persentase percakapan yang mencapai intent:

- High
- Ready to Order

### WhatsApp CTR

Persentase customer yang menekan tombol WhatsApp.

### Recommendation Success

Jumlah percakapan yang menghasilkan rekomendasi produk.

### Unanswered Question Rate

Persentase pertanyaan yang tidak dapat dijawab berdasarkan knowledge base.

---

# 7. Target Users

## Persona 1 — Individual Customer

Membutuhkan 20–50 nasi kotak untuk:

- Arisan
- Pengajian
- Acara keluarga
- Ulang tahun

---

## Persona 2 — Corporate Customer

Membutuhkan 50–500 box untuk:

- Meeting
- Seminar
- Training
- Workshop
- Event perusahaan

---

## Persona 3 — Event Organizer

Membutuhkan jumlah besar dan sering membutuhkan:

- Harga khusus.
- Custom menu.
- Pengiriman.
- Pemesanan dalam jumlah besar.

---

# 8. User Journey

```text
Customer membuka website
        ↓
Melihat Chatbot
        ↓
Customer memulai percakapan
        ↓
AI memahami kebutuhan
        ↓
AI menanyakan informasi yang kurang
        ↓
AI mencari produk relevan
        ↓
AI memberikan rekomendasi
        ↓
Customer mempertimbangkan
        ↓
AI melakukan soft-selling
        ↓
Customer menunjukkan purchase intent
        ↓
AI mengumpulkan data
        ↓
Customer diarahkan ke WhatsApp / Order
```

---

# 9. Core User Flow

### Example

**Customer**

> Saya butuh nasi kotak.

**AI**

> Siap Kak 😊 Untuk berapa box dan acaranya untuk apa?

**Customer**

> 100 box untuk meeting kantor.

**AI**

> Untuk meeting 100 box, saya rekomendasikan Paket Corporate B. Harganya Rp30.000/box dengan menu yang lebih lengkap. Total estimasinya Rp3.000.000. Kalau Kakak punya budget tertentu, saya juga bisa carikan pilihan yang lebih hemat.

**Customer**

> Budget saya 25 ribu.

**AI**

> Bisa Kak 👍 Dengan budget Rp25.000/box, Paket Corporate A lebih cocok. Untuk 100 box estimasinya Rp2.500.000.

**Customer**

> Saya mau pesan.

**AI**

> Siap 😊 Boleh saya minta nama dan nomor WhatsApp yang bisa dihubungi untuk proses pemesanan?

---

# 10. Functional Requirements

## FR-01 — Chat Interface

Website harus menyediakan chatbot widget.

Fitur:

- Open/close chatbot.
- Input text.
- Send message.
- Chat history.
- Loading indicator.
- Error handling.
- Quick reply buttons.

---

# 11. FR-02 — Natural Language Conversation

Chatbot harus dapat memahami pertanyaan natural language.

Contoh:

> "Ada nasi kotak 20 ribuan?"

> "Kalau pesan 100 box dapat harga khusus?"

> "Yang cocok buat rapat kantor apa?"

> "Bisa antar ke daerah X?"

---

# 12. FR-03 — Product Knowledge

Chatbot harus dapat menjawab berdasarkan informasi:

- Nama produk.
- Harga.
- Menu.
- Deskripsi.
- Minimum order.
- Kategori.
- Event suitability.

---

# 13. FR-04 — Product Recommendation

Chatbot harus dapat merekomendasikan produk berdasarkan:

- Budget.
- Quantity.
- Event type.
- Preference.
- Product availability.

Contoh:

```text
Input:

Budget = Rp30.000
Quantity = 100
Event = Meeting

        ↓

Recommendation Engine

        ↓

Corporate Package B
```

---

# 14. FR-05 — Budget Detection

Chatbot harus dapat memahami variasi bahasa:

> "Budget 30 ribuan."

> "Sekitar 25k."

> "Maksimal 30 ribu per box."

Kemudian mengubahnya menjadi structured data.

```json
{
  "budget_per_box": 30000
}
```

---

# 15. FR-06 — Quantity Detection

Chatbot harus dapat memahami:

> "100 orang."

> "Butuh 200 kotak."

> "Untuk sekitar 50 peserta."

Output:

```json
{
  "quantity": 100
}
```

---

# 16. FR-07 — Event Detection

Sistem harus dapat mengenali jenis acara:

- Meeting.
- Pengajian.
- Seminar.
- Training.
- Wedding.
- Arisan.
- Acara keluarga.
- Event lainnya.

---

# 17. FR-08 — Purchase Intent Detection

Intent dibagi menjadi:

### LOW

Customer masih eksplorasi.

Contoh:

> "Ada paket apa?"

### MEDIUM

Customer mulai membandingkan.

> "Kalau 100 box berapa?"

### HIGH

Customer menunjukkan minat membeli.

> "Saya tertarik paket B."

### READY_TO_ORDER

Customer siap membeli.

> "Saya pesan 100 box."

---

# 18. FR-09 — Price Calculation

Backend harus menghitung estimasi harga.

```text
Total Price =
Price Per Box × Quantity
```

Contoh:

```text
Rp30.000 × 100
=
Rp3.000.000
```

LLM tidak boleh menghitung atau menentukan harga sebagai sumber utama.

---

# 19. FR-10 — Upselling

Jika terdapat produk yang lebih premium dan relevan, chatbot dapat menawarkan upgrade.

Contoh:

> "Paket B hanya selisih Rp5.000/box dan sudah mendapatkan tambahan buah. Untuk 100 box, tambahannya Rp500.000."

Upselling harus bersifat:

- Relevan.
- Tidak memaksa.
- Berdasarkan data produk.

---

# 20. FR-11 — Cross-Selling

Chatbot dapat menawarkan produk tambahan apabila tersedia.

Contoh:

> "Selain nasi kotak, Kakak juga bisa menambahkan snack box atau minuman. Mau saya tampilkan?"

---

# 21. FR-12 — Lead Collection

Ketika purchase intent tinggi, sistem mengumpulkan:

- Nama.
- Nomor WhatsApp.
- Jumlah box.
- Paket.
- Tanggal acara.
- Lokasi.
- Catatan.

---

# 22. FR-13 — WhatsApp Handoff

Setelah lead terkumpul, chatbot memberikan CTA:

> "Data pesanannya sudah saya catat. Untuk konfirmasi dan proses pemesanan, Kakak bisa langsung menghubungi admin kami."

Button:

**[Hubungi Admin WhatsApp]**

---

# 23. FR-14 — Human Handoff

Chatbot harus dapat mengalihkan percakapan kepada manusia ketika:

- Customer meminta admin.
- Custom menu.
- Negosiasi harga.
- Permintaan khusus.
- Informasi tidak tersedia.
- Pertanyaan kompleks.

---

# 24. FR-15 — Anti-Hallucination

Chatbot dilarang mengarang:

- Harga.
- Menu.
- Promo.
- Area pengiriman.
- Minimum order.
- Diskon.
- Ketersediaan produk.

Jika data tidak ditemukan:

> "Maaf Kak, informasi tersebut belum tersedia di sistem saya. Agar tidak memberikan informasi yang keliru, saya sarankan langsung menghubungi admin kami."

---

# 25. Technical Architecture

```text
                         WEBSITE
                            │
                            ▼
                    React Chat Widget
                            │
                            ▼
                       FastAPI API
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       Conversation      Sales Logic     Lead Manager
         Manager
             │              │
             └───────┬──────┘
                     ▼
                  RAG Layer
                     │
            ┌────────┴────────┐
            ▼                 ▼
        FAISS Vector      Product Data
          Store            JSON/SQLite
            │
            ▼
        Relevant Context
            │
            ▼
       Gemini 2.5 Flash
            │
            ▼
      Structured / Natural
          Response
            │
            ▼
       Chatbot Frontend
            │
       ┌────┴─────┐
       ▼          ▼
     Product    WhatsApp
      Card       CTA
```

---

# 26. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React |
| Styling | Tailwind CSS |
| Backend | FastAPI |
| LLM | Gemini 2.5 Flash-Lite / Flash |
| Embedding | BGE-M3 |
| Vector Store | FAISS |
| Database | SQLite |
| API | REST |
| Deployment | Render / Railway / VPS |

---

# 27. Why Gemini?

Gemini digunakan karena MVP memiliki deadline satu minggu.

Keuntungan:

- Tidak membutuhkan GPU.
- API integration sederhana.
- Cocok untuk conversational AI.
- Mendukung structured output.
- Mendukung function calling.
- Dapat digunakan untuk multilingual conversation.

Model open-source seperti Qwen dapat menjadi tahap pengembangan berikutnya, tetapi tidak menjadi prioritas MVP.

---

# 28. RAG Architecture

```text
Business Data
     │
     ├── Products
     ├── FAQ
     ├── Promotions
     ├── Delivery
     └── Company Info
            │
            ▼
      Document Loader
            │
            ▼
         Chunking
            │
            ▼
      BGE-M3 Embedding
            │
            ▼
           FAISS
            │
            ▼
       Similarity Search
            │
            ▼
       Top-K Documents
            │
            ▼
     Context Construction
            │
            ▼
          Gemini
            │
            ▼
       Final Response
```

---

# 29. Knowledge Base Structure

```text
knowledge_base/

├── products/
│   ├── paket_hemat_a.md
│   ├── paket_hemat_b.md
│   ├── paket_corporate_a.md
│   └── paket_corporate_b.md
│
├── faq/
│   ├── ordering.md
│   ├── payment.md
│   └── custom_menu.md
│
├── promotion/
│   └── current_promotion.md
│
├── delivery/
│   └── delivery_area.md
│
└── company/
    └── company_profile.md
```

---

# 30. RAG Metadata

Setiap dokumen harus memiliki metadata:

```json
{
  "document_id": "P001",
  "type": "product",
  "category": "corporate",
  "price": 30000,
  "event_types": [
    "meeting",
    "seminar",
    "training"
  ],
  "active": true
}
```

Metadata dapat digunakan untuk membantu filtering sebelum proses retrieval.

---

# 31. RAG Retrieval Strategy

Query customer:

> "100 nasi kotak buat meeting budget 30 ribu."

Sistem melakukan:

```text
Query
 ↓
Semantic Search
 ↓
Top 5 Documents
 ↓
Metadata Filtering
 ↓
Relevant Products
 ↓
Gemini
```

Prioritaskan:

1. Product information.
2. Pricing.
3. Promotion.
4. FAQ.
5. Delivery information.

---

# 32. Database Schema

Untuk MVP gunakan SQLite.

## products

```text
id
name
description
category
price
minimum_order
menu
suitable_for
image_url
active
created_at
updated_at
```

## promotions

```text
id
name
description
discount_type
discount_value
start_date
end_date
conditions
active
```

## leads

```text
id
name
phone
quantity
budget
event_type
event_date
location
product_id
purchase_intent
status
notes
created_at
```

## conversations

```text
id
session_id
sender
message
intent
purchase_intent
created_at
```

---

# 33. API Specification

## POST `/api/chat`

Request:

```json
{
  "session_id": "abc123",
  "message": "Saya butuh 100 nasi kotak untuk meeting"
}
```

Response:

```json
{
  "reply": "Untuk meeting 100 box...",
  "intent": "product_recommendation",
  "purchase_intent": "high",
  "entities": {
    "quantity": 100,
    "event_type": "meeting",
    "budget": null
  },
  "recommendations": [
    {
      "product_id": "P001",
      "name": "Paket Corporate B",
      "price": 30000
    }
  ]
}
```

---

# 34. Structured LLM Output

LLM digunakan untuk ekstraksi intent dan entity.

```json
{
  "intent": "product_recommendation",
  "quantity": 100,
  "budget_per_box": 30000,
  "event_type": "meeting",
  "location": null,
  "event_date": null,
  "purchase_intent": "high"
}
```

Backend kemudian melakukan query terhadap database.

---

# 35. System Prompt

## Role

Kamu adalah **AI Sales Assistant** untuk bisnis nasi kotak.

Tujuanmu adalah membantu pelanggan menemukan paket nasi kotak yang paling sesuai dan membantu mereka melanjutkan ke proses pemesanan.

## Behavior

Kamu harus:

- Ramah.
- Profesional.
- Natural.
- Ringkas.
- Membantu.
- Persuasif secara halus.

## Rules

1. Jangan mengarang informasi.
2. Jangan membuat harga.
3. Jangan membuat promo.
4. Jangan membuat menu.
5. Gunakan knowledge base sebagai sumber informasi bisnis.
6. Jangan memberikan informasi yang tidak ditemukan.
7. Jangan memaksa customer membeli.
8. Jika customer menunjukkan purchase intent tinggi, arahkan ke pemesanan.
9. Jika customer membutuhkan bantuan khusus, arahkan ke admin.

## Sales Strategy

Ketahui bila memungkinkan:

- Quantity.
- Budget.
- Event.
- Location.
- Date.

Jangan menanyakan semua informasi sekaligus.

Ajukan pertanyaan secara natural sesuai konteks.

## Recommendation

Rekomendasikan produk berdasarkan:

- Budget.
- Jumlah.
- Jenis acara.
- Kesesuaian menu.
- Data produk yang tersedia.

## Upselling

Boleh menawarkan produk yang lebih tinggi apabila relevan.

Jelaskan value dan selisih harga secara transparan.

## CTA

Gunakan CTA ketika customer menunjukkan minat tinggi:

- Lihat paket.
- Hitung total.
- Pilih paket.
- Pesan sekarang.
- Hubungi admin.

---

# 36. Conversation Memory

Chatbot harus menyimpan informasi penting selama sesi:

```json
{
  "quantity": 100,
  "budget": 30000,
  "event": "meeting",
  "location": "Malang",
  "selected_product": "P002"
}
```

Sehingga customer tidak perlu mengulang:

> "100 box."

lalu:

> "Budget 30 ribu."

lalu:

> "Untuk meeting."

---

# 37. Frontend UX

Chatbot harus menyediakan:

### Welcome Message

> "Halo Kak 👋 Saya bisa membantu memilih paket nasi kotak sesuai kebutuhan dan budget. Mau pesan untuk acara apa?"

### Quick Actions

```text
[💼 Meeting]
[🎉 Acara]
[🕌 Pengajian]
[💰 Lihat Paket]
```

### Product Card

Menampilkan:

- Foto.
- Nama.
- Harga.
- Menu utama.
- Minimum order.
- CTA.

---

# 38. Error Handling

Jika LLM/API error:

> "Maaf Kak, saya sedang mengalami kendala. Silakan coba beberapa saat lagi atau langsung hubungi admin kami."

Jika RAG tidak menemukan informasi:

> "Untuk informasi tersebut saya belum memiliki datanya. Saya bisa bantu hubungkan Kakak dengan admin."

---

# 39. Security

MVP minimal harus memiliki:

- API key disimpan di environment variable.
- API key tidak boleh berada di frontend.
- Input validation.
- Rate limiting sederhana.
- Sanitization.
- Tidak menyimpan data sensitif yang tidak diperlukan.
- HTTPS pada deployment.

---

# 40. Scope MVP

## Included

| Feature | Status |
|---|---|
| Chat UI | ✅ |
| Gemini integration | ✅ |
| Conversation memory | ✅ |
| Product knowledge | ✅ |
| RAG | ✅ |
| Product recommendation | ✅ |
| Budget detection | ✅ |
| Quantity detection | ✅ |
| Event detection | ✅ |
| Purchase intent | ✅ |
| Price calculation | ✅ |
| Lead collection | ✅ |
| Product cards | ✅ |
| WhatsApp CTA | ✅ |
| Human handoff | ✅ |
| Anti-hallucination | ✅ |

## Excluded

| Feature | Status |
|---|---|
| Payment | ❌ |
| CRM integration | ❌ |
| Complex admin dashboard | ❌ |
| Fine-tuning | ❌ |
| Self-hosted LLM | ❌ |
| Advanced analytics | ❌ |
| Authentication | ❌ |
| Inventory real-time | ❌ |
| Automated order fulfillment | ❌ |

---

# 41. Seven-Day Development Plan

## Day 1 — Business Data & Project Setup

Deliverables:

- Product data.
- FAQ.
- Promotion data.
- Delivery data.
- React project.
- FastAPI project.
- Repository structure.

---

## Day 2 — LLM Integration

Deliverables:

- Gemini API.
- `/api/chat`.
- System prompt.
- Conversation history.
- Basic error handling.

Acceptance:

> User dapat mengirim pesan melalui website dan mendapatkan response AI.

---

## Day 3 — RAG

Deliverables:

- Knowledge base.
- Document loader.
- BGE-M3.
- FAISS.
- Retriever.
- Context injection.

Acceptance:

> AI dapat menjawab pertanyaan berdasarkan data bisnis.

---

## Day 4 — Sales Intelligence

Deliverables:

- Intent detection.
- Entity extraction.
- Budget detection.
- Quantity detection.
- Event detection.
- Product recommendation.
- Price calculation.

Acceptance:

> AI dapat memilih paket berdasarkan kebutuhan customer.

---

## Day 5 — Lead Generation

Deliverables:

- SQLite.
- Lead schema.
- Lead extraction.
- Purchase intent.
- Lead saving.
- WhatsApp CTA.

Acceptance:

> Customer yang siap membeli dapat menghasilkan lead.

---

## Day 6 — Frontend & UX

Deliverables:

- Chat widget.
- Quick actions.
- Product cards.
- CTA.
- Loading state.
- Error state.
- Responsive design.

Acceptance:

> Chatbot terlihat seperti bagian dari website bisnis, bukan prototype backend.

---

## Day 7 — Testing & Deployment

Deliverables:

- Functional testing.
- Hallucination testing.
- Sales scenario testing.
- API testing.
- Deployment.
- Final demo.

---

# 42. Testing Scenario

Minimal 25 test cases.

### Product

> "Berapa harga Paket A?"

### Budget

> "Saya punya budget 25 ribu."

### Quantity

> "Saya butuh 100 box."

### Event

> "Untuk meeting kantor."

### Combined

> "100 box meeting budget 30 ribu."

### Comparison

> "Apa bedanya paket A dan B?"

### Cheapest

> "Yang paling murah apa?"

### Premium

> "Ada paket yang lebih premium?"

### Promotion

> "Ada promo sekarang?"

### Delivery

> "Bisa dikirim ke daerah X?"

### Order

> "Saya mau pesan."

### Custom

> "Bisa custom menu?"

### Human

> "Saya mau bicara dengan admin."

### Hallucination

> "Ada sushi box?"

Bot harus mengatakan bahwa informasi tersebut tidak tersedia jika memang tidak ada dalam knowledge base.

---

# 43. Acceptance Criteria

MVP dinyatakan selesai apabila:

### AC-01

Customer dapat membuka chatbot dari website.

### AC-02

Customer dapat melakukan percakapan natural language.

### AC-03

AI dapat memahami quantity.

### AC-04

AI dapat memahami budget.

### AC-05

AI dapat memahami event.

### AC-06

AI dapat mengambil informasi produk dari knowledge base.

### AC-07

AI dapat memberikan rekomendasi.

### AC-08

Harga yang ditampilkan berasal dari database.

### AC-09

AI dapat menghitung estimasi total.

### AC-10

AI dapat mendeteksi purchase intent.

### AC-11

AI dapat mengumpulkan lead.

### AC-12

Customer dapat diarahkan ke WhatsApp.

### AC-13

AI tidak mengarang informasi bisnis.

### AC-14

Website dapat digunakan pada desktop dan mobile.

---

# 44. Final MVP Architecture

```text
                         CUSTOMER
                            │
                            ▼
                    ┌───────────────┐
                    │  WEBSITE      │
                    │ React + Chat  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │    FastAPI    │
                    └───────┬───────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
        Conversation    Sales Engine    Lead System
          Manager
             │              │
             └───────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │ RAG Engine  │
              └──────┬──────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
            FAISS        SQLite
              │             │
              │        Product Data
              │
              ▼
          Relevant Docs
              │
              ▼
      ┌─────────────────┐
      │ Gemini 2.5      │
      │ Flash-Lite/Flash│
      └────────┬────────┘
               │
               ▼
        AI Sales Response
               │
          ┌────┴─────┐
          ▼          ▼
     Product Card  WhatsApp
```

---

# 45. Final Product Definition

Produk MVP ini bukan sekadar:

> **"Chatbot untuk menjawab pertanyaan customer."**

Tetapi:

> **"AI Sales Assistant berbasis LLM dan RAG yang memahami kebutuhan pelanggan, merekomendasikan paket nasi kotak berdasarkan budget dan jenis acara, menghitung estimasi biaya, mendeteksi purchase intent, dan mengubah percakapan menjadi qualified lead."**

### Core AI Pipeline

```text
Customer Message
       ↓
Intent & Entity Extraction
       ↓
Business Logic
       ↓
RAG Retrieval
       ↓
Product Recommendation
       ↓
LLM Response Generation
       ↓
Sales CTA
       ↓
Lead
       ↓
WhatsApp / Order
```

### Prinsip arsitektur utama

> **LLM memahami pelanggan.**  
> **RAG menyediakan knowledge.**  
> **Database menyimpan fakta bisnis.**  
> **Business logic menentukan keputusan.**  
> **LLM menyampaikan rekomendasi secara natural.**

Dengan scope ini, project **realistis diselesaikan dalam 7 hari**, tetapi tetap cukup kuat untuk dipresentasikan sebagai project **AI Engineer / Generative AI**, bukan sekadar integrasi chatbot API.