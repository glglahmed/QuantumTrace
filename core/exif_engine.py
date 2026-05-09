"""
EXIF Extraction Engine - Full metadata extraction with forensic tagging
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import exifread
except ImportError:
    exifread = None

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
except ImportError:
    Image = None

try:
    import piexif
except ImportError:
    piexif = None

logger = logging.getLogger(__name__)


class EXIFEngine:
    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".tiff", ".tif",
                         ".bmp", ".webp", ".heic"}

    def extract(self, filepath: str) -> Dict[str, Any]:
        result = {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "filesize": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
            "format": os.path.splitext(filepath)[1].lower(),
            "extraction_time": datetime.now().isoformat(),
            "raw_exif": {},
            "camera": {},
            "timestamps": {},
            "gps": {},
            "image_info": {},
            "software": None,
            "errors": []
        }

        try:
            self._extract_pillow(filepath, result)
        except Exception as e:
            result["errors"].append(f"Pillow: {str(e)}")

        try:
            self._extract_exifread(filepath, result)
        except Exception as e:
            result["errors"].append(f"exifread: {str(e)}")

        return result

    def _extract_pillow(self, filepath: str, result: Dict):
        if Image is None:
            return
        with Image.open(filepath) as img:
            result["image_info"]["width"] = img.width
            result["image_info"]["height"] = img.height
            result["image_info"]["mode"] = img.mode
            result["image_info"]["format"] = img.format

            exif_data = img._getexif() if hasattr(img, "_getexif") else None
            if exif_data:
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "GPSInfo":
                        gps = {}
                        for gps_id, gps_val in value.items():
                            gps_tag = GPSTAGS.get(gps_id, gps_id)
                            gps[gps_tag] = str(gps_val)
                        result["gps"]["raw"] = gps
                        result["gps"]["coordinates"] = self._parse_gps(value)
                    elif tag in ("Make", "Model"):
                        result["camera"][tag.lower()] = str(value)
                    elif "DateTime" in str(tag):
                        result["timestamps"][tag] = str(value)
                    elif tag == "Software":
                        result["software"] = str(value)
                    else:
                        result["raw_exif"][tag] = str(value)[:200]

    def _parse_gps(self, gps_info) -> Optional[Dict]:
        try:
            def to_decimal(vals, ref):
                d = float(vals[0].numerator) / float(vals[0].denominator)
                m = float(vals[1].numerator) / float(vals[1].denominator)
                s = float(vals[2].numerator) / float(vals[2].denominator)
                dec = d + m / 60 + s / 3600
                if ref in ("S", "W"):
                    dec = -dec
                return dec
            lat = to_decimal(gps_info[2], gps_info[1])
            lon = to_decimal(gps_info[4], gps_info[3])
            alt = None
            if 6 in gps_info:
                alt_r = gps_info[6]
                alt = float(alt_r.numerator) / float(alt_r.denominator)
            return {"lat": lat, "lon": lon, "altitude": alt}
        except Exception as e:
            logger.debug(f"GPS parse error: {e}")
            return None

    def _extract_exifread(self, filepath: str, result: Dict):
        if exifread is None:
            return
        with open(filepath, "rb") as f:
            tags = exifread.process_file(f, details=False)
            for tag, val in tags.items():
                clean_tag = tag.replace("EXIF ", "").replace("Image ", "").replace("GPS ", "GPS_")
                if clean_tag not in result["raw_exif"]:
                    result["raw_exif"][clean_tag] = str(val)[:200]

    def batch_extract(self, filepaths: list) -> list:
        results = []
        for fp in filepaths:
            if os.path.splitext(fp)[1].lower() in self.SUPPORTED_FORMATS:
                results.append(self.extract(fp))
        return results
