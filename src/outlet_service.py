import os
import json
import math
import requests
from typing import Optional, Tuple, List, Dict, Any

PICKUP_FREE_RADIUS_KM = 3.0       # Gratis jika jarak < 3 km
PICKUP_MANDATORY_THRESHOLD = 25   # < 25 box = wajib pickup

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
        """Geocode alamat ke (lat, lng) via Nominatim dengan fallback daerah Jawa Timur."""
        cleaned_addr = address.strip()
        if not cleaned_addr:
            return None

        # 1. Coba via OpenStreetMap Nominatim
        try:
            url = "https://nominatim.openstreetmap.org/search"
            headers = {"User-Agent": "NasikotakChatbot/1.0"}
            
            # Query 1: As-is
            params = {"q": cleaned_addr, "format": "json", "limit": 1, "countrycodes": "id"}
            response = requests.get(url, params=params, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]["lat"]), float(data[0]["lon"])

            # Query 2: Tambahkan konteks Jawa Timur jika belum ada
            if "jawa timur" not in cleaned_addr.lower() and "surabaya" not in cleaned_addr.lower():
                params["q"] = f"{cleaned_addr}, Jawa Timur"
                response = requests.get(url, params=params, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return float(data[0]["lat"]), float(data[0]["lon"])

            # Query 3: Ambil bagian nama daerah/kota utama
            fallback_part = cleaned_addr.split(",")[-1].strip() if "," in cleaned_addr else cleaned_addr.split()[-1].strip()
            if fallback_part and fallback_part.lower() != cleaned_addr.lower():
                params["q"] = f"{fallback_part}, Jawa Timur"
                response = requests.get(url, params=params, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            print(f"[WARNING] Geocoding network call failed for '{address}': {e}")

        # 2. Fallback kamus koordinat daerah/kecamatan lokal Jawa Timur (Surabaya, Sidoarjo, Gresik, Mojokerto)
        area_coords = {
            "rungkut": (-7.3314, 112.7797),
            "gubeng": (-7.2754, 112.7533),
            "darmo": (-7.2892, 112.7381),
            "wonokromo": (-7.3005, 112.7388),
            "sukolilo": (-7.2892, 112.7885),
            "keputih": (-7.2902, 112.7989),
            "mulyosari": (-7.2705, 112.7969),
            "mulyorejo": (-7.2705, 112.7969),
            "kenjeran": (-7.2470, 112.7738),
            "sidotopo": (-7.2349, 112.7577),
            "platuk": (-7.2324, 112.7638),
            "tambaksari": (-7.2512, 112.7601),
            "genteng": (-7.2595, 112.7482),
            "tegalsari": (-7.2721, 112.7390),
            "sawahan": (-7.2790, 112.7215),
            "tandes": (-7.2648, 112.6628),
            "manukan": (-7.2648, 112.6628),
            "sambikerep": (-7.2776, 112.6591),
            "lontar": (-7.2776, 112.6591),
            "pakuwon": (-7.2776, 112.6591),
            "wiyung": (-7.3101, 112.6953),
            "karangpilang": (-7.3392, 112.7001),
            "gayungan": (-7.3292, 112.7265),
            "ketintang": (-7.3080, 112.7249),
            "wonocolo": (-7.3061, 112.7415),
            "bendul merisi": (-7.3061, 112.7415),
            "waru": (-7.3528, 112.7548),
            "tropodo": (-7.3560, 112.7655),
            "sedati": (-7.3817, 112.7621),
            "betro": (-7.3817, 112.7621),
            "gedangan": (-7.3912, 112.7231),
            "sukodono": (-7.3786, 112.6991),
            "suko": (-7.3786, 112.6991),
            "sidoarjo": (-7.4476, 112.7220),
            "sarirogo": (-7.4223, 112.6764),
            "sepande": (-7.4613, 112.6895),
            "sepanjang": (-7.3522, 112.6913),
            "candi": (-7.4613, 112.6895),
            "krian": (-7.4115, 112.5852),
            "menganti": (-7.2785, 112.5840),
            "hulaan": (-7.2785, 112.5840),
            "gresik": (-7.1659, 112.6544),
            "mojokerto": (-7.4726, 112.4381),
            "mojosari": (-7.5278, 112.5558)
        }

        addr_lower = cleaned_addr.lower()
        for key, coords in area_coords.items():
            if key in addr_lower:
                return coords

        # 3. Fallback pencocokan dengan nama/alamat outlet
        for outlet in self.outlets:
            name_clean = outlet.get("name", "").lower()
            addr_clean = outlet.get("address", "").lower()
            if any(part in addr_lower for part in name_clean.split()) or any(part in addr_clean for part in addr_lower.split() if len(part) > 3):
                return float(outlet["lat"]), float(outlet["lng"])

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


