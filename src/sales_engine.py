import os
from typing import List, Dict, Any, Optional
import time
from openai import OpenAIError
from pydantic import BaseModel, Field
from openai import OpenAI
from sqlalchemy.orm import Session
from dotenv import load_dotenv

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.database import Product, Promotion

load_dotenv()


# Skema Pydantic untuk Output Terstruktur LLM
class MessageAnalysis(BaseModel):
    reasoning: Optional[str] = Field(
        description="Alasan singkat mengapa pesan ini masuk ke intent dan purchase_intent tertentu.",
        default=None,
    )
    intent: str = Field(
        description="Niat utama pengguna. Pilihan: greeting, product_inquiry, product_recommendation, price_calculation, order_intent, promotion_inquiry, delivery_inquiry, complaint, human_request, other"
    )
    purchase_intent: str = Field(
        description="Tingkat ketertarikan beli. Pilihan: LOW, MEDIUM, HIGH, READY_TO_ORDER",
        default="LOW",
    )
    budget: Optional[float] = Field(
        description="Budget per box atau total budget yang disebutkan pengguna, jika ada. Harus angka float, atau null.",
        default=None,
    )
    quantity: Optional[int] = Field(
        description="Jumlah porsi/box yang dibutuhkan, jika ada. Harus angka int, atau null.",
        default=None,
    )
    event_type: Optional[str] = Field(
        description="Jenis acara, misalnya: arisan, pernikahan, meeting, dll. Jika tidak ada, null.",
        default=None,
    )
    location: Optional[str] = Field(
        description="Lokasi acara atau pengiriman, jika ada.", default=None
    )
    event_date: Optional[str] = Field(
        description="Tanggal acara, jika ada.", default=None
    )


class SalesEngine:
    def __init__(self):
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            raise ValueError("GROK_API_KEY tidak ditemukan di .env")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model_name = "llama-3.1-8b-instant"

    def analyze_message(self, message: str) -> MessageAnalysis:
        """
        Menganalisis pesan pengguna menggunakan Gemini untuk mengekstrak intent,
        purchase intent, dan entitas terkait.
        """
        prompt = f"""
        Tugas Anda adalah menganalisis pesan dari pengguna untuk layanan katering nasi kotak.
        
        Pesan Pengguna: "{message}"
        
        Ekstrak informasi berikut dengan akurat dan BERIKAN OUTPUT DALAM FORMAT JSON VALID.
        Struktur JSON yang diharapkan:
        {{
            "reasoning": "Tuliskan analisa singkat (1 kalimat) tentang pesan ini sebelum menentukan intent dan purchase_intent",
            "intent": "Niat utama pengguna. Pilih salah satu: greeting, product_inquiry, product_recommendation, price_calculation, order_intent, promotion_inquiry, delivery_inquiry, complaint, human_request, other",
            "purchase_intent": "Pilih SATU: LOW, MEDIUM, HIGH, atau READY_TO_ORDER",
            "budget": float (angka budget per porsi atau total) atau null,
            "quantity": int (jumlah pesanan) atau null,
            "event_type": string (jenis acara, misalnya: "meeting", "arisan", "pernikahan", dll) atau null. Contoh: "buat meeting di kantor" berarti event_type adalah "meeting",
            "location": string (lokasi acara/pengiriman) atau null,
            "event_date": string (tanggal acara) atau null
        }}
        
        KRITERIA PENENTUAN `purchase_intent` (WAJIB IKUTI PANDUAN INI):

- "LOW": Pengguna hanya menyapa, mengeksplorasi produk, atau bertanya informasi umum tanpa menunjukkan niat membeli yang jelas. Contoh: "Halo", "Ada paket apa aja?", "Menunya apa saja?", "Lokasinya dimana?", "Ada paket untuk acara kantor?"

- "MEDIUM": Pengguna mulai mempertimbangkan pembelian dengan bertanya harga berdasarkan jumlah tertentu, budget, diskon, atau membandingkan paket, tetapi belum menunjukkan keputusan untuk membeli. Contoh: "Kalau pesan 100 harganya?", "Kalau 50 box berapa?", "Budget 30 ribu dapat paket apa?", "Ada diskon kalau pesan banyak?", "Bedanya paket A dan B?"

- "HIGH": Pengguna menunjukkan ketertarikan kuat, persetujuan verbal, atau mengatakan ingin membeli/memesan, tetapi belum memberikan instruksi transaksi konkret seperti alamat, waktu pengiriman, atau pembayaran. Contoh: "Wah menarik, saya mau pesan", "Oke saya ambil paket corporate", "Boleh deh yang itu", "Saya mau paket A", "Saya tertarik dengan paket ini"

- "READY_TO_ORDER": Pengguna sudah memberikan instruksi konkret untuk melakukan transaksi, seperti alamat pengiriman, waktu/tanggal pengiriman, detail pesanan yang siap diproses, atau meminta informasi pembayaran. Contoh: "Kirim ke Sudirman ya besok", "Antar ke kantor saya jam 12", "Saya pesan 100 box untuk hari Jumat", "Minta nomor rekeningnya dong", "Saya mau transfer sekarang", "Kirim 100 box ke Surabaya besok"

ATURAN PENTING:
- Fokus pada maksud keseluruhan pesan, bukan hanya keyword.
- Kata "mau", "pesan", atau jumlah box TIDAK otomatis berarti READY_TO_ORDER.
- "Saya mau pesan 100 box" = HIGH jika belum ada instruksi transaksi konkret.
- "Kirim 100 box ke Sudirman besok" = READY_TO_ORDER.
- "Kalau 100 box harganya berapa?" = MEDIUM.
- Jika pengguna hanya bertanya atau mengeksplorasi = LOW.
- Jika pengguna sedang mempertimbangkan harga/pilihan = MEDIUM.
- Jika pengguna sudah ingin membeli tetapi belum memberikan instruksi transaksi = HIGH.
- Jika pengguna memberikan instruksi transaksi konkret = READY_TO_ORDER.

Pilih tepat satu kategori:
LOW, MEDIUM, HIGH, atau READY_TO_ORDER.
        CATATAN PENTING:
        - Buat "reasoning" terlebih dahulu sebelum field lainnya agar analisis lebih akurat.
        - "intent" dan "purchase_intent" TIDAK BOLEH null.
        - Jika "budget", "quantity", "event_type", "location", "event_date" tidak disebutkan secara eksplisit, berikan nilai null.
        """

        max_retries = 3
        response = None
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "Anda adalah asisten analisis data untuk katering nasi kotak yang selalu mengembalikan JSON valid.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                break
            except OpenAIError as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(
                        f"Rate limit/quota exceeded (429). Menunggu 30 detik sebelum mencoba lagi (Percobaan {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(30)
                else:
                    raise e

        import json

        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            return MessageAnalysis(**data)
        except Exception as e:
            print(f"Error parsing Grok output: {e}")
            # Fallback
            return MessageAnalysis(intent="other", purchase_intent="LOW")

    def recommend_products(
        self,
        db: Session,
        budget: Optional[float] = None,
        quantity: Optional[int] = None,
        event_type: Optional[str] = None,
        limit: int = 3,
    ) -> List[Product]:
        """
        Merekomendasikan produk berdasarkan budget, quantity minimum, dan event type
        dengan membaca file markdown dari knowledge_base/products.
        """
        import os, re

        products = []
        kb_path = os.path.join(
            os.path.dirname(__file__), "..", "knowledge_base", "products"
        )

        if os.path.exists(kb_path):
            for filename in os.listdir(kb_path):
                if filename.endswith(".md"):
                    with open(
                        os.path.join(kb_path, filename), "r", encoding="utf-8"
                    ) as f:
                        content = f.read()
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                lines = parts[1].strip().split("\n")
                                metadata = {}
                                for line in lines:
                                    if ":" in line:
                                        k, v = line.split(":", 1)
                                        k = k.strip()
                                        v = v.strip()
                                        if v.startswith("[") and v.endswith("]"):
                                            v = [x.strip() for x in v[1:-1].split(",")]
                                        elif v.lower() == "true":
                                            v = True
                                        elif v.lower() == "false":
                                            v = False
                                        elif v.isdigit():
                                            v = int(v)
                                        else:
                                            try:
                                                v = float(v)
                                            except ValueError:
                                                pass
                                        metadata[k] = v

                                if not metadata.get("active", True):
                                    continue

                                event_types_list = metadata.get("event_types", [])
                                if isinstance(event_types_list, list):
                                    suitable_for_str = ",".join(event_types_list)
                                else:
                                    suitable_for_str = str(event_types_list)

                                p = Product(
                                    id=metadata.get("document_id", filename),
                                    name=metadata.get(
                                        "name",
                                        filename.replace(".md", "")
                                        .replace("_", " ")
                                        .title(),
                                    ),
                                    price=float(metadata.get("price", 0)),
                                    minimum_order=int(metadata.get("minimum_order", 1)),
                                    category=str(metadata.get("category", "unknown")),
                                    suitable_for=suitable_for_str,
                                )

                                name_match = re.search(r"#\s+(.+)", parts[2])
                                if name_match and "name" not in metadata:
                                    p.name = name_match.group(1).strip()

                                if budget and p.price > budget * 1.05:
                                    continue
                                if quantity and p.minimum_order > quantity:
                                    continue

                                products.append(p)

        # Simple scoring based on event_type
        scored_products = []
        for p in products:
            score = 0
            if event_type and p.suitable_for:
                if event_type.lower() in p.suitable_for.lower():
                    score += 5

            if budget and budget > 0:
                price_ratio = p.price / budget
                score += price_ratio * 3  # Max 3 poin

            scored_products.append((score, p))

        # Urutkan berdasarkan score (descending) lalu harga (descending)
        scored_products.sort(key=lambda x: (x[0], x[1].price), reverse=True)

        # Ambil top N
        return [p for score, p in scored_products[:limit]]

    def calculate_price(
        self, db: Session, product: Product, quantity: int
    ) -> Dict[str, Any]:
        """
        Menghitung total harga dengan mempertimbangkan diskon dari tabel Promotion.
        """
        if quantity < product.minimum_order:
            raise ValueError(
                f"Jumlah pesanan ({quantity}) di bawah minimum order ({product.minimum_order})."
            )

        base_total = product.price * quantity
        discount_amount = 0
        applied_promo = None

        # Ambil satu promosi aktif pertama (Bisa dipercanggih dengan filter tanggal)
        promo = db.query(Promotion).filter(Promotion.active == True).first()
        if promo:
            if promo.discount_type == "percentage":
                discount_amount = base_total * (promo.discount_value / 100)
            elif promo.discount_type == "fixed":
                discount_amount = promo.discount_value
            applied_promo = promo.name

        final_total = max(0, base_total - discount_amount)

        original_price_per_box = product.price
        final_price_per_box = final_total / quantity if quantity > 0 else 0

        return {
            "original_price_per_box": original_price_per_box,
            "final_price_per_box": final_price_per_box,
            "base_total": base_total,
            "discount_amount": discount_amount,
            "final_total": final_total,
            "applied_promo": applied_promo,
        }

    def check_upsell(
        self, db: Session, current_budget: float, quantity: int
    ) -> List[Product]:
        """
        Mencari maksimal 2 produk dengan harga sedikit di atas budget (maksimal 20% lebih tinggi)
        sebagai opsi upselling.
        """
        # Cari produk di range budget -> budget * 1.3
        min_budget = current_budget * 1.01  # Sedikit lebih mahal
        max_budget = current_budget * 1.30  # Maksimal 30% lebih mahal

        products = (
            db.query(Product)
            .filter(Product.active == True)
            .filter(Product.price > min_budget)
            .filter(Product.price <= max_budget)
            .filter(Product.minimum_order <= quantity)
            .order_by(Product.price.asc())
            .limit(2)
            .all()
        )

        return products

    def check_cross_sell(self, db: Session, current_product: Product) -> List[Product]:
        """
        Mencari produk pelengkap (cross-selling) dari knowledge_base/addons.
        Tawarkan 2: 1 beverage dan 1 snack.
        """
        import os, re

        addons = []
        kb_path = os.path.join(
            os.path.dirname(__file__), "..", "knowledge_base", "addons"
        )

        beverage_found = False
        snack_found = False

        if os.path.exists(kb_path):
            for filename in os.listdir(kb_path):
                if filename.endswith(".md"):
                    with open(
                        os.path.join(kb_path, filename), "r", encoding="utf-8"
                    ) as f:
                        content = f.read()
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                lines = parts[1].strip().split("\n")
                                metadata = {}
                                for line in lines:
                                    if ":" in line:
                                        k, v = line.split(":", 1)
                                        metadata[k.strip()] = v.strip()

                                category = metadata.get("category", "").lower()
                                active = (
                                    metadata.get("active", "true").lower() == "true"
                                )

                                if not active:
                                    continue

                                p = Product(
                                    id=metadata.get("document_id", filename),
                                    name=metadata.get("name", ""),
                                    price=float(metadata.get("price", 0)),
                                    category=category,
                                )

                                name_match = re.search(r"#\s+(.+)", parts[2])
                                if name_match and not p.name:
                                    p.name = name_match.group(1).strip()

                                # Extract specific sub-products
                                sub_products = re.findall(
                                    r"^\*\*([^*]+)\*\*", parts[2], re.MULTILINE
                                )
                                if sub_products:
                                    # Prioritize 'Teh Kotak' or 'Snack Box Standar', else use first
                                    selected_sub = None
                                    for sub in sub_products:
                                        if (
                                            "Teh Kotak" in sub
                                            or "Snack Box Standar" in sub
                                        ):
                                            selected_sub = sub
                                            break
                                    if not selected_sub:
                                        selected_sub = sub_products[0]

                                    # If price is in the text (e.g. Snack Box Standar - Rp 10.000 / box)
                                    price_match = re.search(
                                        r"-\s*Rp\s*(\d+)", selected_sub.replace(".", "")
                                    )
                                    if price_match:
                                        p.price = float(price_match.group(1))
                                        p.name = selected_sub.split("-")[0].strip()
                                    else:
                                        p.name = selected_sub

                                if category == "beverage" and not beverage_found:
                                    addons.append(p)
                                    beverage_found = True
                                elif category == "snack" and not snack_found:
                                    addons.append(p)
                                    snack_found = True

                                if beverage_found and snack_found:
                                    break
        return addons
