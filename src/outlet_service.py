import os
import json
import math
import requests
from typing import Optional, Tuple, List, Dict, Any

PICKUP_FREE_RADIUS_KM = 3.0       # Gratis jika jarak < 3 km
PICKUP_MANDATORY_THRESHOLD = 25   # < 25 box = wajib pickup

# Pengelompokan Wilayah Operasional Outlet Ayam Bakar Pak D
AREA_GROUPS = {
    "surabaya_utara": {
        "name": "Surabaya Utara",
        "districts": [
            "Bulak", "Kenjeran", "Krembangan", "Pabean Cantian", "Semampir"
        ],
        "center_coords": (-7.2324, 112.7577),
        "district_coords": {
            "bulak": (-7.2411, 112.7938),
            "kenjeran": (-7.2470, 112.7738),
            "krembangan": (-7.2356, 112.7297),
            "pabean cantian": (-7.2289, 112.7368),
            "pabean cantikan": (-7.2289, 112.7368),
            "semampir": (-7.2185, 112.7483),
            "platuk": (-7.2324, 112.7638),
            "sidotopo": (-7.2349, 112.7577),
            "sidotopo wetan": (-7.2349, 112.7577),
            "surabaya utara": (-7.2324, 112.7577),
            "sby utara": (-7.2324, 112.7577)
        }
    },
    "surabaya_selatan": {
        "name": "Surabaya Selatan",
        "districts": [
            "Dukuh Pakis", "Gayungan", "Jambangan", "Karang Pilang", 
            "Sawahan", "Wiyung", "Wonocolo", "Wonokromo"
        ],
        "center_coords": (-7.3005, 112.7388),
        "district_coords": {
            "dukuh pakis": (-7.2889, 112.7051),
            "gayungan": (-7.3292, 112.7265),
            "jambangan": (-7.3248, 112.7154),
            "karang pilang": (-7.3392, 112.7001),
            "karangpilang": (-7.3392, 112.7001),
            "sawahan": (-7.2790, 112.7215),
            "wiyung": (-7.3101, 112.6953),
            "wonocolo": (-7.3061, 112.7415),
            "wonokromo": (-7.3005, 112.7388),
            "ketintang": (-7.3080, 112.7249),
            "bendul merisi": (-7.3061, 112.7415),
            "jetis": (-7.3080, 112.7337),
            "lidah mertua": (-7.3080, 112.7337),
            "surabaya selatan": (-7.3005, 112.7388),
            "sby selatan": (-7.3005, 112.7388)
        }
    },
    "surabaya_timur": {
        "name": "Surabaya Timur",
        "districts": [
            "Gubeng", "Gunung Anyar", "Mulyorejo", "Rungkut", 
            "Sukolilo", "Tambaksari", "Tenggilis Mejoyo"
        ],
        "center_coords": (-7.2892, 112.7885),
        "district_coords": {
            "gubeng": (-7.2754, 112.7533),
            "gunung anyar": (-7.3389, 112.7925),
            "mulyorejo": (-7.2705, 112.7969),
            "mulyosari": (-7.2705, 112.7969),
            "rungkut": (-7.3314, 112.7797),
            "rungkut madya": (-7.3314, 112.7797),
            "rungkut kidul": (-7.3314, 112.7797),
            "sukolilo": (-7.2892, 112.7885),
            "keputih": (-7.2902, 112.7989),
            "tambaksari": (-7.2512, 112.7601),
            "tenggilis mejoyo": (-7.3204, 112.7632),
            "tenggilis": (-7.3204, 112.7632),
            "surabaya timur": (-7.2892, 112.7885),
            "sby timur": (-7.2892, 112.7885)
        }
    },
    "surabaya_barat": {
        "name": "Surabaya Barat",
        "districts": [
            "Asem Rowo", "Benowo", "Lakarsantri", "Pakal", 
            "Sambikerep", "Sukomanunggal", "Tandes"
        ],
        "center_coords": (-7.2648, 112.6628),
        "district_coords": {
            "asem rowo": (-7.2483, 112.7092),
            "asrowo": (-7.2483, 112.7092),
            "asemrowo": (-7.2483, 112.7092),
            "benowo": (-7.2405, 112.6391),
            "lakarsantri": (-7.3045, 112.6517),
            "lidah kulon": (-7.3058, 112.6617),
            "lidah": (-7.3058, 112.6617),
            "pakal": (-7.2341, 112.6172),
            "sambikerep": (-7.2776, 112.6591),
            "lontar": (-7.2776, 112.6591),
            "pakuwon": (-7.2776, 112.6591),
            "sukomanunggal": (-7.2687, 112.7012),
            "tandes": (-7.2648, 112.6628),
            "manukan": (-7.2648, 112.6628),
            "manukan tengah": (-7.2648, 112.6628),
            "surabaya barat": (-7.2648, 112.6628),
            "sby barat": (-7.2648, 112.6628)
        }
    },
    "surabaya_pusat": {
        "name": "Surabaya Pusat",
        "districts": [
            "Bubutan", "Genteng", "Simokerto", "Tegalsari"
        ],
        "center_coords": (-7.2595, 112.7482),
        "district_coords": {
            "bubutan": (-7.2523, 112.7329),
            "genteng": (-7.2595, 112.7482),
            "simokerto": (-7.2435, 112.7538),
            "tegalsari": (-7.2721, 112.7390),
            "darmo": (-7.2892, 112.7381),
            "surabaya pusat": (-7.2595, 112.7482),
            "sby pusat": (-7.2595, 112.7482)
        }
    },
    "gresik": {
        "name": "Gresik",
        "districts": [
            "Gresik", "Kebomas", "Manyar", "Menganti", "Driyorejo", 
            "Cerme", "Benjeng", "Duduksampeyan", "Kedamean", 
            "Wringinanom", "Bungah", "Sidayu", "Panceng", "Ujungpangkah"
        ],
        "center_coords": (-7.1659, 112.6544),
        "district_coords": {
            "gresik": (-7.1659, 112.6544),
            "kebomas": (-7.1725, 112.6272),
            "manyar": (-7.1264, 112.6053),
            "menganti": (-7.2785, 112.5840),
            "hulaan": (-7.2785, 112.5840),
            "driyorejo": (-7.3486, 112.6288),
            "cerme": (-7.2173, 112.5539),
            "benjeng": (-7.2530, 112.5028),
            "duduksampeyan": (-7.1583, 112.5514),
            "kedamean": (-7.3236, 112.5489),
            "wringinanom": (-7.4042, 112.5292),
            "bungah": (-7.0625, 112.5736),
            "sidayu": (-6.9931, 112.5625)
        }
    },
    "sidoarjo": {
        "name": "Sidoarjo",
        "districts": [
            "Sidoarjo", "Waru", "Sedati", "Gedangan", "Buduran", 
            "Candi", "Porong", "Tanggulangin", "Tulangan", 
            "Krembung", "Sukodono", "Taman", "Krian", "Wonoayu", 
            "Prambon", "Tarik", "Balongbendo", "Jabon"
        ],
        "center_coords": (-7.4476, 112.7220),
        "district_coords": {
            "sidoarjo": (-7.4476, 112.7220),
            "waru": (-7.3528, 112.7548),
            "tropodo": (-7.3560, 112.7655),
            "sedati": (-7.3817, 112.7621),
            "betro": (-7.3817, 112.7621),
            "gedangan": (-7.3912, 112.7231),
            "buduran": (-7.4278, 112.7289),
            "candi": (-7.4613, 112.6895),
            "sepande": (-7.4613, 112.6895),
            "porong": (-7.5389, 112.7028),
            "tanggulangin": (-7.5028, 112.7153),
            "tulangan": (-7.4764, 112.6514),
            "krembung": (-7.5319, 112.6139),
            "sukodono": (-7.3786, 112.6991),
            "suko": (-7.3786, 112.6991),
            "taman": (-7.3522, 112.6913),
            "sepanjang": (-7.3522, 112.6913),
            "krian": (-7.4115, 112.5852),
            "sarirogo": (-7.4223, 112.6764),
            "cemengkalang": (-7.4418, 112.6849),
            "cemeng kalang": (-7.4418, 112.6849),
            "wonoayu": (-7.4333, 112.6167),
            "prambon": (-7.4625, 112.5694),
            "balongbendo": (-7.4139, 112.5194)
        }
    },
    "mojokerto": {
        "name": "Mojokerto",
        "districts": [
            "Magersari", "Prajurit Kulon", "Kranggan", "Mojosari", 
            "Puri", "Dlanggu", "Bangsal", "Ngoro", "Trowulan", 
            "Pacet", "Trawas", "Gedeg", "Jetis Mojokerto", "Sooko"
        ],
        "center_coords": (-7.4726, 112.4381),
        "district_coords": {
            "mojokerto": (-7.4726, 112.4381),
            "mojosari": (-7.5278, 112.5558),
            "magersari": (-7.4694, 112.4417),
            "prajurit kulon": (-7.4778, 112.4278),
            "kranggan": (-7.4833, 112.4444),
            "puri": (-7.5111, 112.4472),
            "dlanggu": (-7.5611, 112.4778),
            "bangsal": (-7.5028, 112.4972),
            "ngoro": (-7.5694, 112.6167),
            "trowulan": (-7.5583, 112.3833),
            "pacet": (-7.6750, 112.5389),
            "trawas": (-7.6694, 112.5972),
            "sooko": (-7.4917, 112.4167)
        }
    },
    "malang": {
        "name": "Malang",
        "districts": [
            "Karang Ploso", "Klojen", "Blimbing", "Lowokwaru", 
            "Sukun", "Kedungkandang", "Singosari", "Lawang", 
            "Dau", "Batu", "Pakis", "Kepanjen"
        ],
        "center_coords": (-7.9797, 112.6304),
        "district_coords": {
            "malang": (-7.9797, 112.6304),
            "karangploso": (-7.8912, 112.5936),
            "karang ploso": (-7.8912, 112.5936),
            "klojen": (-7.9781, 112.6283),
            "blimbing": (-7.9472, 112.6444),
            "lowokwaru": (-7.9444, 112.6139),
            "sukun": (-8.0028, 112.6167),
            "kedungkandang": (-7.9944, 112.6583),
            "singosari": (-7.8925, 112.6658),
            "lawang": (-7.8333, 112.6972),
            "dau": (-7.9417, 112.5667),
            "batu": (-7.8712, 112.5270),
            "pakis": (-7.9528, 112.7167),
            "kepanjen": (-8.1306, 112.5722)
        }
    }
}

# Gabungkan seluruh koordinat kecamatan ke dalam 1 dictionary
ALL_AREA_COORDS: Dict[str, Tuple[float, float]] = {}
for group in AREA_GROUPS.values():
    ALL_AREA_COORDS.update(group["district_coords"])

class OutletService:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "data")
        self.outlets = self._load_outlets()

    def _load_outlets(self) -> List[Dict[str, Any]]:
        """Load outlet data dari JSON file."""
        filepath = os.path.join(self.data_dir, "outlets.json")
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load outlets.json: {e}")
            return []
            
    def get_active_outlets(self) -> List[Dict[str, Any]]:
        return [o for o in self.outlets if o.get("active", True)]

    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode alamat ke (lat, lng) menggunakan kamus kecamatan/daerah lokal, lalu fallback ke Nominatim."""
        cleaned_addr = address.strip()
        if not cleaned_addr:
            return None

        # 1. Cek langsung dari kamus kecamatan & wilayah operasional (sangat cepat & akurat)
        matched_coords = self.get_district_coords(cleaned_addr)
        if matched_coords:
            return matched_coords

        # 2. Cek kecocokan langsung dengan nama/alamat outlet
        addr_lower = cleaned_addr.lower()
        for outlet in self.outlets:
            name_clean = outlet.get("name", "").lower()
            outlet_addr_clean = outlet.get("address", "").lower()
            if any(part in addr_lower for part in name_clean.split()) or any(part in outlet_addr_clean for part in addr_lower.split() if len(part) > 3):
                return float(outlet["lat"]), float(outlet["lng"])

        # 3. Fallback via OpenStreetMap Nominatim untuk alamat jalan spesifik
        try:
            url = "https://nominatim.openstreetmap.org/search"
            headers = {"User-Agent": "NasikotakChatbot/1.0"}
            
            # Query 1: As-is
            params = {"q": cleaned_addr, "format": "json", "limit": 1, "countrycodes": "id"}
            response = requests.get(url, params=params, headers=headers, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]["lat"]), float(data[0]["lon"])

            # Query 2: Tambahkan konteks Jawa Timur jika belum ada
            if "jawa timur" not in cleaned_addr.lower() and "surabaya" not in cleaned_addr.lower():
                params["q"] = f"{cleaned_addr}, Jawa Timur"
                response = requests.get(url, params=params, headers=headers, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            print(f"[WARNING] Geocoding network call failed for '{address}': {e}")

        return None

    def get_district_coords(self, address: str) -> Optional[Tuple[float, float]]:
        """Mencocokkan string alamat dengan kamus kecamatan & wilayah operasional."""
        if not address:
            return None
        addr_lower = address.lower().strip()
        # Urutkan key dari yang terpanjang ke terpendek agar frasa spesifik (mis: 'surabaya timur', 'pabean cantian') dicocokkan lebih dulu
        for key, coords in sorted(ALL_AREA_COORDS.items(), key=lambda x: len(x[0]), reverse=True):
            if key in addr_lower:
                return coords
        return None

    def get_area_group(self, address: str) -> Optional[str]:
        """Mengembalikan nama grup wilayah (misal: 'Surabaya Barat', 'Surabaya Timur', dll) jika cocok."""
        if not address:
            return None
        addr_lower = address.lower().strip()
        for group_id, info in AREA_GROUPS.items():
            if group_id.replace("_", " ") in addr_lower or info["name"].lower() in addr_lower:
                return info["name"]
            for district in info["districts"]:
                if district.lower() in addr_lower:
                    return info["name"]
            for coord_key in info.get("district_coords", {}):
                if coord_key in addr_lower:
                    return info["name"]
        return None

    def haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Hitung jarak dalam km."""
        R = 6371.0 # Radius bumi dalam km
        
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        dlon = lng2_rad - lng1_rad
        dlat = lat2_rad - lat1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c

    def calculate_pickup_cost(self, distance_km: float) -> int:
        """Hitung ongkir pickup."""
        if distance_km < PICKUP_FREE_RADIUS_KM:
            return 0
        return -1

    def is_pickup_mandatory(self, quantity: Optional[int]) -> bool:
        """Return True jika pesanan wajib pickup (qty < 25)."""
        if quantity is None:
            return False
        return quantity < PICKUP_MANDATORY_THRESHOLD

    def get_delivery_options(self, quantity: Optional[int]) -> List[str]:
        """Return opsi yang tersedia berdasarkan qty."""
        if self.is_pickup_mandatory(quantity):
            return ["pickup"]
        return ["delivery", "pickup"]

    def find_nearest_outlets(self, user_lat: float, user_lng: float, limit: int = 5) -> List[Dict[str, Any]]:
        """Return outlet terdekat beserta jarak dan ongkir (default 5 outlet)."""
        active_outlets = self.get_active_outlets()
        
        results = []
        for outlet in active_outlets:
            dist = self.haversine_distance(user_lat, user_lng, outlet["lat"], outlet["lng"])
            cost = self.calculate_pickup_cost(dist)
            
            outlet_info = dict(outlet)
            outlet_info["distance_km"] = round(dist, 1)
            outlet_info["pickup_cost"] = cost
            
            results.append(outlet_info)
            
        # Sort by distance
        results.sort(key=lambda x: x["distance_km"])
        
        return results[:limit]

    def find_nearest_by_address(self, address: str, limit: int = 5) -> Optional[List[Dict[str, Any]]]:
        """Gabungan geocode + find nearest (default 5 outlet). Return None jika geocode gagal."""
        coords = self.geocode_address(address)
        if not coords:
            return None
            
        lat, lng = coords
        return self.find_nearest_outlets(lat, lng, limit)

    def format_outlet_info(
        self,
        outlets_with_distance: List[Dict[str, Any]],
        include_cost: bool = True
    ) -> str:
        """Format daftar outlet untuk chat, termasuk jarak dan estimasi ongkir."""
        if not outlets_with_distance:
            return "Maaf, kami tidak dapat menemukan outlet di sekitar lokasi tersebut."
            
        lines = []
        is_single = len(outlets_with_distance) == 1
        for i, outlet in enumerate(outlets_with_distance, 1):
            name = outlet.get("name", "Outlet Pak D")
            dist = outlet.get("distance_km", 0)
            cost = outlet.get("pickup_cost", 0)
            addr = outlet.get("address", "")
            hours = outlet.get("operational_hours")
            
            hours_str = f" | Buka {hours}" if hours else ""
            
            cost_str = ""
            if include_cost:
                if cost == 0:
                    cost_str = " (Ongkir: GRATIS ✅)"
                elif cost == -1:
                    cost_str = " (Ongkir: Diskusikan dengan Admin 👨‍💻)"
                else:
                    cost_str = f" (Ongkir: Rp {cost:,.0f})".replace(",", ".")
                    
            if is_single:
                line1 = f"📍 {name} — {dist} km{cost_str}"
                line2 = f"{addr}{hours_str}"
            else:
                line1 = f"{i}. 📍 {name} — {dist} km{cost_str}"
                line2 = f"   {addr}{hours_str}"
            
            lines.append(line1)
            lines.append(line2)
            
        return "\n".join(lines)

    def match_outlet_from_input(self, text: str, candidate_outlets: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
        """Mencocokkan pilihan user (misal: 'nomor 1', '1', 'pilihan 2', atau nama cabang) ke data outlet."""
        if not text:
            return None
            
        text_lower = text.lower().strip()
        candidates = candidate_outlets if candidate_outlets else self.get_active_outlets()
        
        # 1. Cek pola urutan angka ("nomor 1", "opsi 2", "pilih 1", atau angka tunggal)
        import re
        num_match = re.search(r'\b(?:nomor|no\.?|opsi|pilihan)?\s*([1-5])\b', text_lower)
        if num_match and candidate_outlets:
            idx = int(num_match.group(1)) - 1
            if 0 <= idx < len(candidate_outlets):
                return candidate_outlets[idx]
                
        # 2. Cek kecocokan nama cabang pada candidates
        for outlet in candidates:
            name_raw = outlet.get("name", "").lower()
            name_simple = name_raw.replace("pak d - ", "").strip()
            if name_simple and name_simple in text_lower:
                return outlet
            if name_raw in text_lower:
                return outlet
                
        # 3. Cek ke seluruh outlet aktif
        for outlet in self.get_active_outlets():
            name_raw = outlet.get("name", "").lower()
            name_simple = name_raw.replace("pak d - ", "").strip()
            if name_simple and name_simple in text_lower:
                return outlet
                
        return None

    def get_outlet_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Mencari data outlet berdasarkan nama atau id."""
        if not name:
            return None
        return self.match_outlet_from_input(name)

    def validate_reservation_time(self, time_str: str) -> Tuple[bool, Optional[str]]:
        """
        Validasi apakah jam reservasi berada dalam rentang jam operasional (10:00 - 21:30 WIB).
        Return (is_valid, warning_message).
        """
        if not time_str:
            return True, None
            
        import re
        text = time_str.lower().strip()
        hour = None
        minute = 0
        
        # Coba format HH:MM atau HH.MM
        m = re.search(r'(\d{1,2})[:.](\d{2})', text)
        if m:
            hour = int(m.group(1))
            minute = int(m.group(2))
        else:
            # Coba format angka (misal "jam 4 sore", "jam 7 malam", "16")
            m2 = re.search(r'(\d{1,2})', text)
            if m2:
                hour = int(m2.group(1))
                
        if hour is None:
            return True, None
            
        # Konversi 12-hour ke 24-hour jika ada penanda sore/malam
        if any(w in text for w in ["sore", "malam", "pm"]) and hour < 12:
            hour += 12
        elif any(w in text for w in ["pagi", "am"]) and hour == 12:
            hour = 0
            
        time_decimal = hour + (minute / 60.0)
        
        # Jam operasional standar: 10:00 s/d 21:30 WIB
        if time_decimal < 10.0:
            return False, f"Jam kedatangan ({time_str}) di luar jam operasional. Outlet Ayam Bakar Pak D baru buka mulai pukul 10.00 WIB."
        elif time_decimal > 21.5:
            return False, f"Jam kedatangan ({time_str}) di luar jam operasional. Outlet Ayam Bakar Pak D tutup pukul 22.00 WIB."
            
        return True, None


