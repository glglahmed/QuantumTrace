"""
Metadata Anomaly Detection Engine - Rule-based forensic anomaly detection
"""

import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

EDITING_SOFTWARE = [
    "photoshop", "lightroom", "gimp", "snapseed", "affinity",
    "capture one", "darktable", "rawtherapee", "pixelmator",
    "paint.net", "canva", "vsco", "facetune", "luminar",
    "adobe", "corel", "on1", "skylum"
]


class AnomalyDetector:
    SEVERITY = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

    def analyze(self, metadata: Dict) -> List[Dict]:
        anomalies = []
        anomalies.extend(self._check_missing_metadata(metadata))
        anomalies.extend(self._check_software(metadata))
        anomalies.extend(self._check_timestamps(metadata))
        anomalies.extend(self._check_gps(metadata))
        anomalies.extend(self._check_exif_structure(metadata))
        anomalies.extend(self._check_image_integrity(metadata))
        return anomalies

    def _check_missing_metadata(self, meta: Dict) -> List[Dict]:
        issues = []
        if not meta.get("raw_exif"):
            issues.append({"type": "MISSING_EXIF", "severity": "HIGH",
                           "detail": "No EXIF metadata found — possible stripping or forgery",
                           "field": "EXIF"})
        if not meta.get("gps", {}).get("coordinates"):
            issues.append({"type": "MISSING_GPS", "severity": "MEDIUM",
                           "detail": "No GPS coordinates embedded in image",
                           "field": "GPS"})
        if not meta.get("timestamps"):
            issues.append({"type": "MISSING_TIMESTAMP", "severity": "HIGH",
                           "detail": "No timestamp metadata found — metadata may have been wiped",
                           "field": "DateTime"})
        if not meta.get("camera"):
            issues.append({"type": "MISSING_CAMERA_INFO", "severity": "MEDIUM",
                           "detail": "No camera make/model — possible screenshot or edited image",
                           "field": "Camera"})
        return issues

    def _check_software(self, meta: Dict) -> List[Dict]:
        issues = []
        sw = (meta.get("software") or "").lower()
        if sw:
            for editor in EDITING_SOFTWARE:
                if editor in sw:
                    issues.append({"type": "EDITING_SOFTWARE_DETECTED", "severity": "HIGH",
                                   "detail": f"Image processed with editing software: {meta.get('software')}",
                                   "field": "Software"})
                    break
        return issues

    def _check_timestamps(self, meta: Dict) -> List[Dict]:
        issues = []
        now = datetime.now()
        timestamps = meta.get("timestamps", {})

        for ts_key, ts_val in timestamps.items():
            try:
                dt = datetime.strptime(str(ts_val)[:19], "%Y:%m:%d %H:%M:%S")
                if dt > now:
                    issues.append({"type": "FUTURE_TIMESTAMP", "severity": "CRITICAL",
                                   "detail": f"{ts_key} is set in the future: {ts_val}",
                                   "field": ts_key})
                if dt.year < 2000:
                    issues.append({"type": "SUSPICIOUS_OLD_DATE", "severity": "MEDIUM",
                                   "detail": f"Unusually old timestamp: {ts_val}",
                                   "field": ts_key})
            except Exception:
                pass

        ts_vals = list(timestamps.values())
        if len(ts_vals) >= 2:
            try:
                t1 = datetime.strptime(str(ts_vals[0])[:19], "%Y:%m:%d %H:%M:%S")
                t2 = datetime.strptime(str(ts_vals[1])[:19], "%Y:%m:%d %H:%M:%S")
                diff = abs((t2 - t1).total_seconds())
                if diff > 86400:
                    issues.append({"type": "TIMESTAMP_MISMATCH", "severity": "MEDIUM",
                                   "detail": f"Timestamp discrepancy of {diff/3600:.1f}h between fields",
                                   "field": "DateTime"})
            except Exception:
                pass
        return issues

    def _check_gps(self, meta: Dict) -> List[Dict]:
        issues = []
        coords = meta.get("gps", {}).get("coordinates")
        if coords:
            lat, lon = coords.get("lat", 0), coords.get("lon", 0)
            if lat == 0.0 and lon == 0.0:
                issues.append({"type": "NULL_ISLAND_GPS", "severity": "CRITICAL",
                               "detail": "GPS at (0,0) — Null Island, likely spoofed or default",
                               "field": "GPS"})
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                issues.append({"type": "INVALID_GPS_RANGE", "severity": "CRITICAL",
                               "detail": f"GPS coordinates out of valid range: {lat:.4f}, {lon:.4f}",
                               "field": "GPS"})
        return issues

    def _check_exif_structure(self, meta: Dict) -> List[Dict]:
        issues = []
        errors = meta.get("errors", [])
        if errors:
            issues.append({"type": "EXIF_PARSE_ERRORS", "severity": "MEDIUM",
                           "detail": f"EXIF parsing errors detected: {'; '.join(errors[:3])}",
                           "field": "EXIF Structure"})
        return issues

    def _check_image_integrity(self, meta: Dict) -> List[Dict]:
        issues = []
        info = meta.get("image_info", {})
        w = info.get("width", 0)
        h = info.get("height", 0)
        if w > 0 and h > 0:
            ratio = max(w, h) / min(w, h)
            if ratio > 10:
                issues.append({"type": "UNUSUAL_ASPECT_RATIO", "severity": "LOW",
                               "detail": f"Unusual aspect ratio {w}x{h} — may indicate cropping",
                               "field": "Dimensions"})
        return issues

    def severity_score(self, anomalies: List[Dict]) -> int:
        return sum(self.SEVERITY.get(a.get("severity", "LOW"), 1) for a in anomalies)

#hhhuvggggggggggghjkv
