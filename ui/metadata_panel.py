"""
Evidence & Metadata Panel - Evidence table and EXIF detail viewer
"""
import json
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

TABLE_STYLE = """
QTableWidget {
    background: #161b22;
    gridline-color: #21262d;
    border: none;
    font-size: 10px;
    selection-background-color: #1c2128;
}
QTableWidget::item { padding: 4px 6px; color: #c9d1d9; }
QTableWidget::item:selected { background: #1c2128; color: #00d4ff; }
QHeaderView::section {
    background: #21262d; color: #7d8590;
    padding: 6px; border: none; font-size: 10px;
    font-family: Consolas;
}
QTableWidget::item:alternate { background: #0d1117; }
QScrollBar:vertical { background:#161b22; width:8px; }
QScrollBar::handle:vertical { background:#30363d; border-radius:4px; }
"""

TREE_STYLE = """
QTreeWidget {
    background: #161b22; border: none;
    font-size: 10px; color: #c9d1d9;
    font-family: Consolas;
}
QTreeWidget::item { padding: 3px 6px; }
QTreeWidget::item:selected { background: #1c2128; color: #00d4ff; }
QHeaderView::section {
    background: #21262d; color: #7d8590;
    padding: 6px; border: none;
    font-family: Consolas;
}
QScrollBar:vertical { background:#161b22; width:8px; }
QScrollBar::handle:vertical { background:#30363d; border-radius:4px; }
"""


class MetadataPanel(QWidget):

    def __init__(self):
        super().__init__()
        self._evidence_data = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: Evidence list ──────────────────────────────────────────────
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 10, 5, 10)

        hdr = QLabel("📁  EVIDENCE INVENTORY")
        hdr.setStyleSheet(
            "color:#00d4ff; font-size:11px; font-weight:bold; "
            "padding:4px; border-bottom:1px solid #21262d;")
        ll.addWidget(hdr)

        self.evidence_table = QTableWidget()
        self.evidence_table.setColumnCount(6)
        self.evidence_table.setHorizontalHeaderLabels(
            ["Filename", "Fmt", "Size", "GPS", "Anomalies", "Status"])
        hh = self.evidence_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3, 4, 5):
            hh.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.evidence_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.evidence_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.evidence_table.setAlternatingRowColors(True)
        self.evidence_table.setStyleSheet(TABLE_STYLE)
        self.evidence_table.itemSelectionChanged.connect(self._on_select)
        ll.addWidget(self.evidence_table)
        splitter.addWidget(left)

        # ── Right: Detail tree ───────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(5, 10, 10, 10)

        hdr2 = QLabel("🔍  METADATA DETAIL")
        hdr2.setStyleSheet(
            "color:#00d4ff; font-size:11px; font-weight:bold; "
            "padding:4px; border-bottom:1px solid #21262d;")
        rl.addWidget(hdr2)

        self.detail_tree = QTreeWidget()
        self.detail_tree.setHeaderLabels(["Field", "Value"])
        self.detail_tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.detail_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.detail_tree.setStyleSheet(TREE_STYLE)
        self.detail_tree.setIndentation(14)
        rl.addWidget(self.detail_tree)
        splitter.addWidget(right)

        splitter.setSizes([460, 520])
        layout.addWidget(splitter)

    def add_evidence(self, result: dict):
        self._evidence_data.append(result)
        meta = result.get("metadata", {})
        anomalies = result.get("anomalies", [])
        validation = result.get("validation", {})

        row = self.evidence_table.rowCount()
        self.evidence_table.insertRow(row)

        def cell(text, align=Qt.AlignLeft):
            item = QTableWidgetItem(str(text))
            item.setTextAlignment(align | Qt.AlignVCenter)
            return item

        fn_item = cell(meta.get("filename", "unknown"))
        fn_item.setData(Qt.UserRole, len(self._evidence_data) - 1)
        self.evidence_table.setItem(row, 0, fn_item)

        self.evidence_table.setItem(
            row, 1, cell(meta.get("format", "").upper().lstrip("."), Qt.AlignCenter))

        size = meta.get("filesize", 0)
        self.evidence_table.setItem(
            row, 2, cell(f"{size/1024:.0f}K" if size < 1048576
                         else f"{size/1048576:.1f}M", Qt.AlignCenter))

        has_gps = bool(meta.get("gps", {}).get("coordinates"))
        gps_item = cell("✓" if has_gps else "✗", Qt.AlignCenter)
        gps_item.setForeground(QColor("#3fb950" if has_gps else "#f78166"))
        self.evidence_table.setItem(row, 3, gps_item)

        an_count = len(anomalies)
        an_item = cell(str(an_count), Qt.AlignCenter)
        if an_count > 0:
            an_item.setForeground(QColor("#f78166"))
        self.evidence_table.setItem(row, 4, an_item)

        overall = validation.get("overall_status", "?")
        status_item = cell(overall, Qt.AlignCenter)
        col = {"PASS": "#3fb950", "WARN": "#d29922",
               "FAIL": "#f78166"}.get(overall, "#7d8590")
        status_item.setForeground(QColor(col))
        self.evidence_table.setItem(row, 5, status_item)

    def _on_select(self):
        rows = self.evidence_table.selectedItems()
        if not rows:
            return
        idx = self.evidence_table.item(rows[0].row(), 0).data(Qt.UserRole)
        if idx is not None and idx < len(self._evidence_data):
            self._show_detail(self._evidence_data[idx])

    def _show_detail(self, result: dict):
        self.detail_tree.clear()
        meta = result.get("metadata", {})

        bold_font = QFont("Consolas", 10, QFont.Bold)

        def section(title: str, data: dict, color: str = "#00d4ff"):
            root = QTreeWidgetItem([title, ""])
            root.setForeground(0, QColor(color))
            root.setFont(0, bold_font)
            for k, v in data.items():
                child = QTreeWidgetItem([str(k), str(v)[:160]])
                child.setForeground(0, QColor("#c9d1d9"))
                child.setForeground(1, QColor("#7d8590"))
                root.addChild(child)
            self.detail_tree.addTopLevelItem(root)
            root.setExpanded(True)
            return root

        section("📄 File Info", {
            "Filename": meta.get("filename", ""),
            "Full Path": meta.get("filepath", ""),
            "Format": meta.get("format", "").upper(),
            "File Size": f"{meta.get('filesize', 0):,} bytes",
            "SHA-256": result.get("sha256", "N/A"),
            "MD5": result.get("md5", "N/A"),
            "Extraction Time": meta.get("extraction_time", "")
        })

        if meta.get("image_info"):
            info = meta["image_info"]
            section("🖼 Image", {
                "Dimensions": f"{info.get('width', 0)} × {info.get('height', 0)} px",
                "Color Mode": info.get("mode", ""),
                "Format": info.get("format", "")
            }, "#58a6ff")

        if meta.get("camera"):
            section("📷 Camera", meta["camera"], "#58a6ff")

        if meta.get("timestamps"):
            section("📅 Timestamps", meta["timestamps"], "#d29922")

        coords = meta.get("gps", {}).get("coordinates")
        if coords:
            section("📍 GPS Coordinates", {
                "Latitude": f"{coords.get('lat', 0):.8f}°",
                "Longitude": f"{coords.get('lon', 0):.8f}°",
                "Altitude": f"{coords.get('altitude', 'N/A')} m",
                "Maps Link": (f"https://maps.google.com/?q="
                              f"{coords.get('lat',0)},{coords.get('lon',0)}")
            }, "#3fb950")

        if meta.get("software"):
            section("💻 Software", {"Software": meta["software"]}, "#d29922")

        validation = result.get("validation", {})
        if validation.get("checks"):
            v_data = {}
            for c in validation["checks"]:
                v_data[c["check"]] = f"[{c['status']}]  {c['detail']}"
            overall = validation.get("overall_status", "?")
            col = {"PASS": "#3fb950", "WARN": "#d29922",
                   "FAIL": "#f78166"}.get(overall, "#7d8590")
            section(f"✅ Validation  [{overall}]", v_data, col)

        anomalies = result.get("anomalies", [])
        if anomalies:
            an_data = {}
            for a in anomalies:
                key = f"[{a.get('severity','?')}] {a.get('type','')}"
                an_data[key] = a.get("detail", "")
            section(f"⚠️ Anomalies  ({len(anomalies)})", an_data, "#f78166")

        raw = dict(list(meta.get("raw_exif", {}).items())[:40])
        if raw:
            section("🔬 Raw EXIF  (first 40 tags)", raw, "#3d4450")
