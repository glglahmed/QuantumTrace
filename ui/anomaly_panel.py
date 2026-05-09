"""
Anomaly Panel - Severity-grouped anomaly display with live badge counters
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

logger = logging.getLogger(__name__)

SEV_COLORS = {
    "CRITICAL": "#ff2222",
    "HIGH": "#ff7b00",
    "MEDIUM": "#d29922",
    "LOW": "#3fb950"
}
SEV_BG = {
    "CRITICAL": "#1a0000",
    "HIGH": "#1a0a00",
    "MEDIUM": "#1a1400",
    "LOW": "#001a08"
}
SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


class BadgeWidget(QFrame):
    def __init__(self, label: str, color: str):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background: #161b22;
                border: 1px solid {color};
                border-radius: 4px;
            }}
        """)
        self.setFixedWidth(130)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(10, 8, 10, 8)

        self._count = QLabel("0")
        self._count.setStyleSheet(
            f"color:{color}; font-size:26px; font-weight:bold; "
            f"font-family:Consolas; background:transparent;")
        self._count.setAlignment(Qt.AlignCenter)

        self._label = QLabel(label)
        self._label.setStyleSheet(
            "color:#7d8590; font-size:9px; font-family:Consolas; "
            "background:transparent;")
        self._label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self._count)
        layout.addWidget(self._label)

    def set_count(self, n: int):
        self._count.setText(str(n))


class AnomalyPanel(QWidget):

    def __init__(self):
        super().__init__()
        self._anomaly_data = []
        self._counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        hdr_bar = QWidget()
        hdr_bar.setStyleSheet(
            "background:#161b22; border-bottom:1px solid #30363d;")
        hdr_layout = QHBoxLayout(hdr_bar)
        hdr_layout.setContentsMargins(14, 8, 14, 8)

        hdr = QLabel("⚠️  ANOMALY DETECTION REPORT")
        hdr.setStyleSheet(
            "color:#f78166; font-size:11px; font-weight:bold;")
        hdr_layout.addWidget(hdr)
        hdr_layout.addStretch()

        self.total_lbl = QLabel("0 anomalies detected")
        self.total_lbl.setStyleSheet("color:#7d8590; font-size:10px;")
        hdr_layout.addWidget(self.total_lbl)
        layout.addWidget(hdr_bar)

        # Badge row
        badge_bar = QWidget()
        badge_bar.setStyleSheet(
            "background:#0d1117; border-bottom:1px solid #21262d;")
        badge_layout = QHBoxLayout(badge_bar)
        badge_layout.setContentsMargins(14, 10, 14, 10)
        badge_layout.setSpacing(10)

        self.badge_critical = BadgeWidget("CRITICAL", SEV_COLORS["CRITICAL"])
        self.badge_high = BadgeWidget("HIGH", SEV_COLORS["HIGH"])
        self.badge_medium = BadgeWidget("MEDIUM", SEV_COLORS["MEDIUM"])
        self.badge_low = BadgeWidget("LOW", SEV_COLORS["LOW"])

        for badge in [self.badge_critical, self.badge_high,
                      self.badge_medium, self.badge_low]:
            badge_layout.addWidget(badge)

        badge_layout.addStretch()

        # Legend
        legend_widget = QWidget()
        legend_layout = QVBoxLayout(legend_widget)
        legend_layout.setSpacing(3)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        for sev, desc in [
            ("CRITICAL", "GPS spoofing, future timestamps, Null Island"),
            ("HIGH", "Missing EXIF, editing software, missing timestamps"),
            ("MEDIUM", "Timestamp mismatch, missing GPS, parse errors"),
            ("LOW", "Unusual dimensions, minor inconsistencies")
        ]:
            lbl = QLabel(
                f"<span style='color:{SEV_COLORS[sev]}'>{sev}</span>"
                f"<span style='color:#3d4450;'> — {desc}</span>")
            lbl.setStyleSheet("font-size:9px; font-family:Consolas;")
            legend_layout.addWidget(lbl)
        badge_layout.addWidget(legend_widget)
        layout.addWidget(badge_bar)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(
            ["File", "Anomaly Type", "Severity", "Field", "Detail"])
        hh = self.tree.header()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(False)
        self.tree.setRootIsDecorated(False)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: #0d1117;
                border: none;
                font-family: Consolas;
                font-size: 10px;
                color: #c9d1d9;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px 6px;
                border-bottom: 1px solid #161b22;
            }
            QTreeWidget::item:selected { background: #1c2128; color: #00d4ff; }
            QTreeWidget::item:hover { background: #111820; }
            QHeaderView::section {
                background: #21262d; color: #7d8590;
                padding: 6px; border: none;
                font-family: Consolas; font-size: 10px;
            }
            QScrollBar:vertical { background:#0d1117; width:8px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:4px; }
        """)
        layout.addWidget(self.tree)

    def add_anomalies(self, filename: str, anomalies: list):
        self._anomaly_data.append((filename, anomalies))

        sorted_an = sorted(anomalies,
                           key=lambda x: SEV_ORDER.get(x.get("severity", "LOW"), 3))

        for a in sorted_an:
            sev = a.get("severity", "LOW")
            self._counts[sev] = self._counts.get(sev, 0) + 1

            item = QTreeWidgetItem([
                filename[:28],
                (a.get("type") or "")[:32],
                sev,
                (a.get("field") or "")[:18],
                (a.get("detail") or "")[:90]
            ])
            item.setForeground(2, QColor(SEV_COLORS.get(sev, "#7d8590")))
            item.setForeground(0, QColor("#c9d1d9"))
            item.setForeground(1, QColor("#a0a8b0"))
            item.setForeground(3, QColor("#58a6ff"))
            item.setForeground(4, QColor("#7d8590"))

            bg = SEV_BG.get(sev)
            if bg:
                for col in range(5):
                    item.setBackground(col, QColor(bg))

            self.tree.addTopLevelItem(item)

        self._update_badges()

    def _update_badges(self):
        total = sum(self._counts.values())
        self.total_lbl.setText(f"{total} anomalies detected")
        self.badge_critical.set_count(self._counts.get("CRITICAL", 0))
        self.badge_high.set_count(self._counts.get("HIGH", 0))
        self.badge_medium.set_count(self._counts.get("MEDIUM", 0))
        self.badge_low.set_count(self._counts.get("LOW", 0))
