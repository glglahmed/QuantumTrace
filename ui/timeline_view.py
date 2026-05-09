"""
Timeline View - Chronological evidence display with movement path info
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QFrame, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class TimelineView(QWidget):

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        hdr_bar = QWidget()
        hdr_bar.setStyleSheet("background:#161b22; border-bottom:1px solid #30363d;")
        hdr_layout = QHBoxLayout(hdr_bar)
        hdr_layout.setContentsMargins(14, 8, 14, 8)

        hdr = QLabel("📅  FORENSIC TIMELINE RECONSTRUCTION")
        hdr.setStyleSheet("color:#00d4ff; font-size:11px; font-weight:bold;")
        hdr_layout.addWidget(hdr)
        hdr_layout.addStretch()

        self.summary_lbl = QLabel("No timeline data")
        self.summary_lbl.setStyleSheet("color:#7d8590; font-size:10px;")
        hdr_layout.addWidget(self.summary_lbl)
        layout.addWidget(hdr_bar)

        # Column headers
        col_bar = QWidget()
        col_bar.setStyleSheet("background:#1c2128; border-bottom:1px solid #21262d;")
        col_layout = QHBoxLayout(col_bar)
        col_layout.setContentsMargins(12, 4, 12, 4)
        for label, width in [("#", 40), ("Timestamp", 160), ("Filename", 220),
                              ("GPS Coordinates", 180), ("Camera", 180), ("Anomalies", 80)]:
            lbl = QLabel(label)
            lbl.setStyleSheet("color:#7d8590; font-size:9px; font-family:Consolas;")
            lbl.setFixedWidth(width)
            col_layout.addWidget(lbl)
        col_layout.addStretch()
        layout.addWidget(col_bar)

        # Timeline list
        self.timeline_list = QListWidget()
        self.timeline_list.setStyleSheet("""
            QListWidget {
                background: #0d1117;
                border: none;
                font-family: Consolas;
                font-size: 10px;
                color: #c9d1d9;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 12px;
                border-bottom: 1px solid #161b22;
            }
            QListWidget::item:selected {
                background: #1c2128;
                color: #00d4ff;
            }
            QListWidget::item:hover { background: #161b22; }
            QScrollBar:vertical { background:#0d1117; width:8px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:4px; }
        """)
        layout.addWidget(self.timeline_list)

        # Gap warning bar (initially hidden)
        self.gap_bar = QLabel("")
        self.gap_bar.setStyleSheet(
            "background:#2d1b00; color:#d29922; padding:6px 14px; "
            "font-size:10px; border-top:1px solid #d29922;")
        self.gap_bar.hide()
        layout.addWidget(self.gap_bar)

    def load_timeline(self, timeline_data: list):
        self.timeline_list.clear()
        self.gap_bar.hide()

        if not timeline_data:
            self.summary_lbl.setText("No timeline data available")
            item = QListWidgetItem(
                "  No timestamped evidence loaded. Import images to build the timeline.")
            item.setForeground(QColor("#3d4450"))
            self.timeline_list.addItem(item)
            return

        gps_count = sum(1 for t in timeline_data
                        if t.get("gps", {}).get("coordinates"))
        first_ts = timeline_data[0].get("_timeline_ts")
        last_ts = timeline_data[-1].get("_timeline_ts")
        span = ""
        if first_ts and last_ts:
            diff = (last_ts - first_ts).total_seconds() / 3600
            span = f"  |  Span: {diff:.1f}h"

        self.summary_lbl.setText(
            f"{len(timeline_data)} events  |  {gps_count} with GPS{span}")

        # Check for time gaps
        gaps = []
        for i in range(1, len(timeline_data)):
            t1 = timeline_data[i-1].get("_timeline_ts")
            t2 = timeline_data[i].get("_timeline_ts")
            if t1 and t2:
                diff_h = (t2 - t1).total_seconds() / 3600
                if diff_h > 24:
                    gaps.append(f"{diff_h:.0f}h gap between "
                                f"#{i} and #{i+1}")

        if gaps:
            self.gap_bar.setText(
                "⚠  Time gaps detected: " + "  |  ".join(gaps[:3]))
            self.gap_bar.show()

        for i, item_data in enumerate(timeline_data):
            ts = item_data.get("_timeline_ts")
            ts_str = ts.strftime("%Y-%m-%d  %H:%M:%S") if ts else "Unknown time      "
            filename = (item_data.get("filename") or "unknown")[:30]
            coords = item_data.get("gps", {}).get("coordinates")
            gps_str = (f"{coords['lat']:.5f}, {coords['lon']:.5f}"
                       if coords else "No GPS data         ")
            camera = item_data.get("camera", {})
            cam = f"{camera.get('make','')} {camera.get('model','')}".strip()
            cam = (cam or "Unknown")[:22]
            an_count = len(item_data.get("anomalies", []))

            text = (f"  {i+1:04d}   {ts_str}   {filename:<30}   "
                    f"{gps_str:<28}   {cam:<22}   "
                    f"{'⚠ ' + str(an_count) if an_count else '✓ 0'}")

            list_item = QListWidgetItem(text)
            list_item.setData(Qt.UserRole, i)

            # Alternating row colors
            if i % 2 == 0:
                list_item.setBackground(QColor("#0d1117"))
            else:
                list_item.setBackground(QColor("#111820"))

            if coords:
                list_item.setForeground(QColor("#c9d1d9"))
            else:
                list_item.setForeground(QColor("#5a6270"))

            if an_count > 0:
                list_item.setForeground(QColor("#d29922"))

            self.timeline_list.addItem(list_item)
