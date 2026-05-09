"""
Timeline Reconstruction Engine - Chronological sorting and movement analysis
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class TimelineEngine:

    def build_timeline(self, evidence_list: List[Dict]) -> List[Dict]:
        """Sort evidence chronologically by best available timestamp."""
        timed = []
        for ev in evidence_list:
            ts = self._extract_best_timestamp(ev)
            if ts:
                timed.append({**ev, "_timeline_ts": ts})

        timed.sort(key=lambda x: x["_timeline_ts"])
        return timed

    def _extract_best_timestamp(self, meta: Dict) -> Optional[datetime]:
        ts_fields = meta.get("timestamps", {})
        priority = ["DateTimeOriginal", "DateTime", "DateTimeDigitized"]
        for field in priority:
            if field in ts_fields:
                try:
                    return datetime.strptime(str(ts_fields[field])[:19], "%Y:%m:%d %H:%M:%S")
                except Exception:
                    pass
        for val in ts_fields.values():
            try:
                return datetime.strptime(str(val)[:19], "%Y:%m:%d %H:%M:%S")
            except Exception:
                pass
        return None

    def get_movement_path(self, timeline: List[Dict]) -> List[Dict]:
        """Extract ordered GPS path from timeline."""
        path = []
        for item in timeline:
            coords = item.get("gps", {}).get("coordinates")
            if coords and coords.get("lat") and coords.get("lon"):
                path.append({
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "timestamp": item["_timeline_ts"],
                    "filename": item.get("filename", ""),
                    "filepath": item.get("filepath", "")
                })
        return path

    def detect_gaps(self, timeline: List[Dict], gap_hours: float = 24.0) -> List[Dict]:
        """Detect large time gaps in the timeline."""
        gaps = []
        for i in range(1, len(timeline)):
            t1 = timeline[i - 1].get("_timeline_ts")
            t2 = timeline[i].get("_timeline_ts")
            if t1 and t2:
                diff = (t2 - t1).total_seconds() / 3600
                if diff > gap_hours:
                    gaps.append({
                        "before": timeline[i - 1].get("filename"),
                        "after": timeline[i].get("filename"),
                        "gap_hours": round(diff, 2)
                    })
        return gaps

    def get_summary(self, timeline: List[Dict]) -> Dict:
        if not timeline:
            return {}
        first = timeline[0].get("_timeline_ts")
        last = timeline[-1].get("_timeline_ts")
        span = (last - first).total_seconds() / 3600 if first and last else 0
        gps_count = sum(1 for t in timeline if t.get("gps", {}).get("coordinates"))
        return {
            "total_events": len(timeline),
            "first_event": first.isoformat() if first else "N/A",
            "last_event": last.isoformat() if last else "N/A",
            "span_hours": round(span, 2),
            "events_with_gps": gps_count
        }
