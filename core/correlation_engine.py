"""
Correlation Engine - Evidence correlation by time, location, and anomaly patterns
"""

import math
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class CorrelationEngine:

    def correlate(self, evidence_list: List[Dict],
                  time_window_hours: float = 1.0,
                  distance_km: float = 5.0) -> List[Dict]:
        """Find groups of correlated images by time and/or location."""
        groups = []
        used = set()

        for i, ev1 in enumerate(evidence_list):
            if i in used:
                continue
            group = [ev1]
            used.add(i)
            for j, ev2 in enumerate(evidence_list):
                if j <= i or j in used:
                    continue
                if self._are_correlated(ev1, ev2, time_window_hours, distance_km):
                    group.append(ev2)
                    used.add(j)
            if len(group) > 1:
                groups.append({
                    "images": [g.get("filename", "") for g in group],
                    "count": len(group),
                    "type": "TIME_LOCATION_CLUSTER",
                    "anchor": group[0].get("filename", "")
                })

        return groups

    def _are_correlated(self, ev1: Dict, ev2: Dict,
                        time_window_h: float, dist_km: float) -> bool:
        return (self._check_time_proximity(ev1, ev2, time_window_h) or
                self._check_location_proximity(ev1, ev2, dist_km))

    def _check_time_proximity(self, ev1: Dict, ev2: Dict, hours: float) -> bool:
        try:
            ts1 = ev1.get("_timeline_ts")
            ts2 = ev2.get("_timeline_ts")
            if ts1 and ts2:
                return abs((ts2 - ts1).total_seconds()) <= hours * 3600
        except Exception:
            pass
        return False

    def _check_location_proximity(self, ev1: Dict, ev2: Dict, km: float) -> bool:
        try:
            c1 = ev1.get("gps", {}).get("coordinates")
            c2 = ev2.get("gps", {}).get("coordinates")
            if c1 and c2:
                dist = self._haversine(c1["lat"], c1["lon"], c2["lat"], c2["lon"])
                return dist <= km
        except Exception:
            pass
        return False

    def _haversine(self, lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = (math.sin(dphi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
        return 2 * R * math.asin(math.sqrt(a))

    def find_device_clusters(self, evidence_list: List[Dict]) -> Dict[str, List]:
        """Group evidence by camera device."""
        devices = {}
        for ev in evidence_list:
            camera = ev.get("camera", {})
            key = f"{camera.get('make','')} {camera.get('model','')}".strip() or "Unknown"
            devices.setdefault(key, []).append(ev.get("filename", ""))
        return devices
