import os
import json
import math
import requests
from typing import Optional, Tuple, List, Dict, Any

PICKUP_FREE_RADIUS_KM = 3.0       # Gratis jika jarak < 3 km
PICKUP_COST_PER_KM = 2000         # Rp 2.000 per km jika >= 3 km
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
        """Geocode alamat ke (lat, lng) via Nominatim."""
        try:
            url = "https://nominatim.openstreetmap.org/search"
            # Limit search to Indonesia
            params = {
                "q": address,
                "format": "json",
                "limit": 1,
                "countrycodes": "id"
            }
            # Nominatim requires a valid user agent
            headers = {
                "User-Agent": "NasikotakChatbot/1.0"
            }
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])
                return lat, lng
            return None
        except Exception as e:
            print(f"[ERROR] Geocoding failed for '{address}': {e}")
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
        return int(distance_km * PICKUP_COST_PER_KM)

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

    def find_nearest_outlets(self, user_lat: float, user_lng: float, limit: int = 3) -> List[Dict[str, Any]]:
        """Return outlet terdekat beserta jarak dan ongkir."""
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

    def find_nearest_by_address(self, address: str, limit: int = 3) -> Optional[List[Dict[str, Any]]]:
        """Gabungan geocode + find nearest. Return None jika geocode gagal."""
        coords = self.geocode_address(address)
        if not coords:
            return None
            
        lat, lng = coords
        return self.find_nearest_outlets(lat, lng, limit)

    def format_outlet_info(self, outlets_with_distance: List[Dict[str, Any]]) -> str:
        """Format daftar outlet untuk chat, termasuk jarak dan estimasi ongkir."""
        if not outlets_with_distance:
            return "Maaf, kami tidak dapat menemukan outlet di sekitar lokasi tersebut."
            
        lines = []
        for i, outlet in enumerate(outlets_with_distance, 1):
            name = outlet.get("name", "Outlet Pak D")
            dist = outlet.get("distance_km", 0)
            cost = outlet.get("pickup_cost", 0)
            addr = outlet.get("address", "")
            hours = outlet.get("operational_hours", "")
            
            if cost == 0:
                cost_str = "GRATIS ✅"
            else:
                # Format ke rupiah
                cost_str = f"Rp {cost:,.0f}".replace(",", ".")
                
            line1 = f"{i}. 📍 {name} — {dist} km (Ongkir: {cost_str})"
            line2 = f"   {addr} | Buka {hours}"
            
            lines.append(line1)
            lines.append(line2)
            
        return "\n".join(lines)
