import os
from typing import List, Dict, Any, Optional
import time
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import Product, Promotion
from src.llm_service import LLMService

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
    package_name: Optional[str] = Field(
        description="Nama paket/produk yang direkomendasikan atau dipilih customer, jika ada.",
        default=None,
    )
    delivery_time: Optional[str] = Field(
        description="Jam pengiriman/pengambilan yang disebut customer, jika ada.",
        default=None,
    )
    fulfillment_method: Optional[str] = Field(
        description="'delivery' atau 'pickup', jika bisa disimpulkan dari qty atau pernyataan eksplisit customer.",
        default=None,
    )

class SalesEngine:
    def __init__(self):
        self.llm = LLMService()

    def analyze_message(self, message: str) -> MessageAnalysis:
        """
        Menganalisis pesan pengguna menggunakan LLMService terpusat untuk mengekstrak intent,
        purchase intent, dan entitas terkait.
        """
        result = self.llm.chat_structured(message)
        
        # Mapping result from LLMService to MessageAnalysis schema
        entities = result.get("entities", {})
        
        return MessageAnalysis(
            intent=result.get("intent", "other"),
            purchase_intent=result.get("purchase_intent", "LOW"),
            budget=entities.get("budget_per_box"),
            quantity=entities.get("quantity"),
            event_type=entities.get("event_type"),
            location=entities.get("location"),
            event_date=entities.get("event_date"),
            package_name=entities.get("package_name"),
            delivery_time=entities.get("delivery_time"),
            fulfillment_method=entities.get("fulfillment_method"),
        )

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
        Mencari 1 produk dengan harga sedikit di atas budget (maksimal 30% lebih tinggi)
        sebagai opsi upselling, diambil yang terdekat dengan budget saat ini.
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
            .limit(1)
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