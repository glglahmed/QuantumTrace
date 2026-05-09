"""
Validation Engine - Forensic correctness and integrity validation
"""

import os
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class ValidationEngine:

    def validate(self, metadata: Dict, filepath: str) -> Dict:
        results = {
            "filepath": filepath,
            "overall_status": "PASS",
            "checks": [],
            "timestamp": datetime.now().isoformat()
        }

        checks = [
            self._validate_file_exists(filepath),
            self._validate_exif_completeness(metadata),
            self._validate_gps(metadata),
            self._validate_timestamps(metadata),
            self._validate_image_info(metadata),
            self._validate_file_size(filepath),
        ]

        results["checks"] = checks
        failed = [c for c in checks if c["status"] == "FAIL"]
        warnings = [c for c in checks if c["status"] == "WARN"]

        if failed:
            results["overall_status"] = "FAIL"
        elif warnings:
            results["overall_status"] = "WARN"

        results["failed_count"] = len(failed)
        results["warning_count"] = len(warnings)
        results["passed_count"] = len([c for c in checks if c["status"] == "PASS"])
        return results

    def _validate_file_exists(self, filepath: str) -> Dict:
        exists = os.path.exists(filepath)
        size = os.path.getsize(filepath) if exists else 0
        return {
            "check": "File Existence",
            "status": "PASS" if (exists and size > 0) else "FAIL",
            "detail": f"Exists: {exists} | Size: {size:,} bytes"
        }

    def _validate_file_size(self, filepath: str) -> Dict:
        if not os.path.exists(filepath):
            return {"check": "File Size", "status": "FAIL", "detail": "File not found"}
        size = os.path.getsize(filepath)
        if size < 100:
            return {"check": "File Size", "status": "FAIL",
                    "detail": f"Suspiciously small file: {size} bytes"}
        if size > 500 * 1024 * 1024:
            return {"check": "File Size", "status": "WARN",
                    "detail": f"Very large file: {size/(1024*1024):.1f} MB"}
        return {"check": "File Size", "status": "PASS",
                "detail": f"{size / 1024:.1f} KB"}

    def _validate_exif_completeness(self, meta: Dict) -> Dict:
        has_exif = bool(meta.get("raw_exif"))
        has_camera = bool(meta.get("camera"))
        has_ts = bool(meta.get("timestamps"))
        score = sum([has_exif, has_camera, has_ts])
        status = "PASS" if score == 3 else ("WARN" if score >= 1 else "FAIL")
        return {
            "check": "EXIF Completeness",
            "status": status,
            "detail": f"EXIF data: {has_exif} | Camera info: {has_camera} | Timestamps: {has_ts}"
        }

    def _validate_gps(self, meta: Dict) -> Dict:
        coords = meta.get("gps", {}).get("coordinates")
        if not coords:
            return {"check": "GPS Validity", "status": "WARN",
                    "detail": "No GPS data present in image"}
        lat, lon = coords.get("lat", 0), coords.get("lon", 0)
        valid_range = (-90 <= lat <= 90) and (-180 <= lon <= 180)
        not_null = not (lat == 0.0 and lon == 0.0)
        status = "PASS" if (valid_range and not_null) else "FAIL"
        return {
            "check": "GPS Validity",
            "status": status,
            "detail": f"Lat: {lat:.6f} | Lon: {lon:.6f} | In range: {valid_range}"
        }

    def _validate_timestamps(self, meta: Dict) -> Dict:
        ts = meta.get("timestamps", {})
        if not ts:
            return {"check": "Timestamp Validity", "status": "FAIL",
                    "detail": "No timestamps found"}
        now = datetime.now()
        for key, val in ts.items():
            try:
                dt = datetime.strptime(str(val)[:19], "%Y:%m:%d %H:%M:%S")
                if dt > now:
                    return {"check": "Timestamp Validity", "status": "FAIL",
                            "detail": f"Future timestamp in {key}: {val}"}
            except Exception:
                pass
        return {"check": "Timestamp Validity", "status": "PASS",
                "detail": f"{len(ts)} timestamp(s) validated successfully"}

    def _validate_image_info(self, meta: Dict) -> Dict:
        info = meta.get("image_info", {})
        w = info.get("width", 0)
        h = info.get("height", 0)
        status = "PASS" if (w > 0 and h > 0) else "WARN"
        return {
            "check": "Image Dimensions",
            "status": status,
            "detail": f"{w} × {h} pixels | Mode: {info.get('mode', 'unknown')}"
        }
