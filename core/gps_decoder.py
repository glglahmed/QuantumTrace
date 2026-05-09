"""
GPS Decoder - DMS to Decimal, reverse geocoding, spoof detection, Haversine
"""
import math
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False


class GPSDecoder:
    EARTH_RADIUS_KM = 6371.0

    def __init__(self):
        self.geocoder = Nominatim(user_agent="forensix_dfir_v1") if GEOPY_AVAILABLE else None

    def dms_to_decimal(self, degrees: float, minutes: float,
                        seconds: float, direction: str) -> float:
        decimal = degrees + minutes / 60 + seconds / 3600
        if direction in ("S", "W"):
            decimal = -decimal
        return round(decimal, 8)

    def validate_coordinates(self, lat: float, lon: float) -> Dict:
        result = {"valid": True, "issues": []}
        if not (-90 <= lat <= 90):
            result["valid"] = False
            result["issues"].append(f"Invalid latitude: {lat}")
        if not (-180 <= lon <= 180):
            result["valid"] = False
            result["issues"].append(f"Invalid longitude: {lon}")
        if lat == 0.0 and lon == 0.0:
            result["issues"].append("Null Island (0,0) - possible spoof")
        return result

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        if not self.geocoder:
            return f"({lat:.4f}, {lon:.4f})"
        try:
            loc = self.geocoder.reverse(f"{lat}, {lon}", timeout=5)
            return loc.address if loc else None
        except Exception as e:
            logger.debug(f"Reverse geocode failed: {e}")
            return f"({lat:.4f}, {lon:.4f})"

    def haversine_distance(self, lat1: float, lon1: float,
                            lat2: float, lon2: float) -> float:
        """Distance in km using Haversine formula."""
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
        return 2 * self.EARTH_RADIUS_KM * math.asin(math.sqrt(a))

    def detect_impossible_travel(self, points: list) -> list:
        """Detect movement faster than commercial aircraft (900 km/h)."""
        anomalies = []
        MAX_SPEED_KMH = 900
        for i in range(1, len(points)):
            p1, p2 = points[i - 1], points[i]
            try:
                dist = self.haversine_distance(p1["lat"], p1["lon"],
                                               p2["lat"], p2["lon"])
                dt = (p2["timestamp"] - p1["timestamp"]).total_seconds() / 3600
                if dt > 0:
                    speed = dist / dt
                    if speed > MAX_SPEED_KMH:
                        anomalies.append({
                            "type": "impossible_travel",
                            "from": p1,
                            "to": p2,
                            "distance_km": round(dist, 2),
                            "speed_kmh": round(speed, 2),
                            "max_allowed": MAX_SPEED_KMH
                        })
            except Exception as e:
                logger.debug(f"Travel check error: {e}")
        return anomalies
