"""
Evidence Manager - SQLite storage, chain of custody, and evidence retrieval
"""

import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join("database", "evidence.db")


class EvidenceManager:

    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._conn()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE,
            filename TEXT,
            sha256 TEXT,
            md5 TEXT,
            filesize INTEGER,
            format TEXT,
            added_at TEXT,
            metadata_json TEXT,
            has_gps INTEGER DEFAULT 0,
            lat REAL,
            lon REAL,
            timestamp_original TEXT,
            camera_make TEXT,
            camera_model TEXT,
            software TEXT
        );
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id INTEGER,
            anomaly_type TEXT,
            severity TEXT,
            detail TEXT,
            field TEXT,
            detected_at TEXT,
            FOREIGN KEY(evidence_id) REFERENCES evidence(id)
        );
        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id INTEGER,
            check_name TEXT,
            status TEXT,
            detail TEXT,
            overall_status TEXT,
            validated_at TEXT,
            FOREIGN KEY(evidence_id) REFERENCES evidence(id)
        );
        CREATE TABLE IF NOT EXISTS custody_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id INTEGER,
            action TEXT,
            details TEXT,
            operator TEXT,
            timestamp TEXT,
            FOREIGN KEY(evidence_id) REFERENCES evidence(id)
        );
        CREATE TABLE IF NOT EXISTS gps_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evidence_id INTEGER,
            lat REAL,
            lon REAL,
            altitude REAL,
            timestamp TEXT,
            address TEXT,
            FOREIGN KEY(evidence_id) REFERENCES evidence(id)
        );
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized at %s", self.db_path)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def add_evidence(self, metadata: Dict, sha256: str, md5: str) -> int:
        conn = self._conn()
        c = conn.cursor()
        coords = metadata.get("gps", {}).get("coordinates") or {}
        ts_fields = metadata.get("timestamps", {})
        ts_orig = ts_fields.get("DateTimeOriginal") or ts_fields.get("DateTime") or ""
        camera = metadata.get("camera", {})

        try:
            c.execute("""
            INSERT OR REPLACE INTO evidence
            (filepath, filename, sha256, md5, filesize, format, added_at,
             metadata_json, has_gps, lat, lon, timestamp_original,
             camera_make, camera_model, software)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                metadata.get("filepath", ""),
                metadata.get("filename", ""),
                sha256, md5,
                metadata.get("filesize", 0),
                metadata.get("format", ""),
                datetime.now().isoformat(),
                json.dumps(metadata, default=str),
                1 if coords else 0,
                coords.get("lat"),
                coords.get("lon"),
                str(ts_orig),
                camera.get("make", ""),
                camera.get("model", ""),
                metadata.get("software", "")
            ))
            conn.commit()
            ev_id = c.lastrowid
            self._log_custody(conn, ev_id, "INGESTED", f"SHA256:{sha256[:16]}...", "ForensiX")
            return ev_id
        except Exception as e:
            logger.error(f"DB insert error: {e}")
            return -1
        finally:
            conn.close()

    def add_anomalies(self, evidence_id: int, anomalies: List[Dict]):
        conn = self._conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        for a in anomalies:
            c.execute("""
            INSERT INTO anomalies (evidence_id, anomaly_type, severity, detail, field, detected_at)
            VALUES (?,?,?,?,?,?)
            """, (evidence_id, a.get("type"), a.get("severity"),
                  a.get("detail"), a.get("field"), now))
        conn.commit()
        conn.close()

    def add_validation(self, evidence_id: int, validation: Dict):
        conn = self._conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        overall = validation.get("overall_status", "UNKNOWN")
        for check in validation.get("checks", []):
            c.execute("""
            INSERT INTO validation_results (evidence_id, check_name, status, detail, overall_status, validated_at)
            VALUES (?,?,?,?,?,?)
            """, (evidence_id, check.get("check"), check.get("status"),
                  check.get("detail"), overall, now))
        conn.commit()
        conn.close()

    def get_all_evidence(self) -> List[Dict]:
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM evidence ORDER BY added_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_evidence_by_id(self, ev_id: int) -> Optional[Dict]:
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM evidence WHERE id=?", (ev_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    def get_anomalies(self, evidence_id: int = None) -> List[Dict]:
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        if evidence_id:
            rows = conn.execute("SELECT * FROM anomalies WHERE evidence_id=?",
                                (evidence_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM anomalies ORDER BY detected_at DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_gps_points(self) -> List[Dict]:
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
        SELECT e.id, e.filename, e.lat, e.lon, e.timestamp_original,
               e.camera_make, e.camera_model
        FROM evidence e WHERE e.has_gps=1 AND e.lat IS NOT NULL
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict:
        conn = self._conn()
        c = conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        with_gps = c.execute("SELECT COUNT(*) FROM evidence WHERE has_gps=1").fetchone()[0]
        anomaly_count = c.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]
        critical = c.execute("SELECT COUNT(*) FROM anomalies WHERE severity='CRITICAL'").fetchone()[0]
        high = c.execute("SELECT COUNT(*) FROM anomalies WHERE severity='HIGH'").fetchone()[0]
        conn.close()
        return {
            "total_images": total,
            "with_gps": with_gps,
            "total_anomalies": anomaly_count,
            "critical_anomalies": critical,
            "high_anomalies": high
        }

    def get_custody_log(self, evidence_id: int = None) -> List[Dict]:
        conn = self._conn()
        conn.row_factory = sqlite3.Row
        if evidence_id:
            rows = conn.execute(
                "SELECT * FROM custody_log WHERE evidence_id=? ORDER BY timestamp",
                (evidence_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM custody_log ORDER BY timestamp").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def _log_custody(self, conn, ev_id: int, action: str, details: str, operator: str):
        conn.execute("""
        INSERT INTO custody_log (evidence_id, action, details, operator, timestamp)
        VALUES (?,?,?,?,?)
        """, (ev_id, action, details, operator, datetime.now().isoformat()))
        conn.commit()

    def clear_all(self):
        """Clear all evidence from the database."""
        conn = self._conn()
        conn.executescript("""
        DELETE FROM anomalies;
        DELETE FROM validation_results;
        DELETE FROM custody_log;
        DELETE FROM gps_points;
        DELETE FROM evidence;
        """)
        conn.commit()
        conn.close()
