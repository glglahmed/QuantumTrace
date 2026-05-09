"""
Hash Engine - SHA256 file integrity and chain of custody
"""
import hashlib
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HashEngine:
    def __init__(self):
        self.hash_log = []

    def compute_sha256(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            result = sha256.hexdigest()
            self._log_hash(filepath, result)
            return result
        except Exception as e:
            logger.error(f"Hash error for {filepath}: {e}")
            return ""

    def compute_md5(self, filepath: str) -> str:
        md5 = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception as e:
            logger.error(f"MD5 error: {e}")
            return ""

    def verify_integrity(self, filepath: str, expected_hash: str) -> bool:
        return self.compute_sha256(filepath) == expected_hash

    def _log_hash(self, filepath: str, hash_val: str):
        self.hash_log.append({
            "timestamp": datetime.now().isoformat(),
            "file": filepath,
            "sha256": hash_val,
            "size": os.path.getsize(filepath) if os.path.exists(filepath) else 0
        })

    def get_log(self):
        return self.hash_log
