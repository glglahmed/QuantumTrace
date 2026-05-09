"""
ForensiX Main Dashboard - Primary application window with drag & drop
"""
import os
import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QFileDialog,
    QStatusBar, QFrame, QProgressBar,
    QMessageBox, QToolBar, QApplication, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QIcon

from core.exif_engine import EXIFEngine
from core.hash_engine import HashEngine
from core.anomaly_detector import AnomalyDetector
from core.validation_engine import ValidationEngine
from core.evidence_manager import EvidenceManager
from core.live_map_engine import LiveMapEngine
from core.timeline_engine import TimelineEngine
from core.correlation_engine import CorrelationEngine
from core.report_generator import ReportGenerator
from core.heatmap_engine import HeatmapEngine

from ui.metadata_panel import MetadataPanel
from ui.live_map_view import LiveMapView
from ui.timeline_view import TimelineView
from ui.anomaly_panel import AnomalyPanel

logger = logging.getLogger(__name__)

# ── Global stylesheet ─────────────────────────────────────────────────────────
STYLE = """
* { font-family: Consolas, 'Courier New', monospace; }

QMainWindow, QWidget {
    background-color: #0d1117;
    color: #c9d1d9;
}

QTabWidget::pane {
    border: none;
    background: #0d1117;
}
QTabBar {
    background: #161b22;
    border-bottom: 1px solid #30363d;
}
QTabBar::tab {
    background: #161b22;
    color: #7d8590;
    padding: 9px 22px;
    border-right: 1px solid #21262d;
    font-size: 11px;
    min-width: 120px;
}
QTabBar::tab:selected {
    background: #0d1117;
    color: #00d4ff;
    border-top: 2px solid #00d4ff;
}
QTabBar::tab:hover:!selected {
    background: #1c2128;
    color: #c9d1d9;
}

QPushButton {
    background: #161b22;
    color: #00d4ff;
    border: 1px solid #00d4ff;
    padding: 5px 14px;
    font-size: 11px;
    min-height: 26px;
}
QPushButton:hover {
    background: #1c2128;
    border-color: #58a6ff;
    color: #58a6ff;
}
QPushButton:pressed { background: #0d1117; }
QPushButton:disabled { color: #3d4450; border-color: #21262d; }
QPushButton#danger {
    color: #f78166; border-color: #f78166;
}
QPushButton#danger:hover {
    background: #1a0a08; border-color: #ff4444; color: #ff4444;
}

QLabel { color: #c9d1d9; }

QStatusBar {
    background: #161b22;
    color: #7d8590;
    border-top: 1px solid #21262d;
    font-size: 10px;
    padding: 2px 8px;
}
QStatusBar::item { border: none; }

QProgressBar {
    background: #21262d;
    border: none;
    height: 4px;
    border-radius: 2px;
}
QProgressBar::chunk { background: #00d4ff; border-radius: 2px; }

QToolBar {
    background: #161b22;
    border-bottom: 1px solid #30363d;
    spacing: 4px;
    padding: 4px 8px;
}
QToolBar::separator {
    background: #30363d;
    width: 1px;
    margin: 4px 6px;
}

QSplitter::handle { background: #30363d; }
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical { height: 1px; }

QMessageBox {
    background: #161b22;
    color: #c9d1d9;
}
QMessageBox QPushButton {
    min-width: 80px;
}

QFileDialog {
    background: #161b22;
}
"""


class IngestWorker(QThread):
    """Background worker — runs the full ingestion pipeline per file."""
    progress = pyqtSignal(int, str)
    result   = pyqtSignal(dict)
    finished = pyqtSignal(int, int)   # success_count, error_count
    error    = pyqtSignal(str)

    def __init__(self, filepaths: list):
        super().__init__()
        self.filepaths = filepaths
        self.exif_engine       = EXIFEngine()
        self.hash_engine       = HashEngine()
        self.anomaly_detector  = AnomalyDetector()
        self.validation_engine = ValidationEngine()
        self.evidence_manager  = EvidenceManager()

    def run(self):
        total   = len(self.filepaths)
        success = 0
        errors  = 0

        for i, fp in enumerate(self.filepaths):
            try:
                self.progress.emit(
                    int(((i + 0.5) / total) * 100),
                    os.path.basename(fp))

                meta       = self.exif_engine.extract(fp)
                sha256     = self.hash_engine.compute_sha256(fp)
                md5        = self.hash_engine.compute_md5(fp)
                anomalies  = self.anomaly_detector.analyze(meta)
                validation = self.validation_engine.validate(meta, fp)

                ev_id = self.evidence_manager.add_evidence(meta, sha256, md5)
                if ev_id > 0:
                    self.evidence_manager.add_anomalies(ev_id, anomalies)
                    self.evidence_manager.add_validation(ev_id, validation)

                self.result.emit({
                    "id":         ev_id,
                    "metadata":   meta,
                    "anomalies":  anomalies,
                    "validation": validation,
                    "sha256":     sha256,
                    "md5":        md5,
                    "filepath":   fp
                })
                success += 1
            except Exception as e:
                errors += 1
                logger.error(f"Ingest error [{fp}]: {e}")
                self.error.emit(f"{os.path.basename(fp)}: {str(e)}")

        self.progress.emit(100, "Complete")
        self.finished.emit(success, errors)


# ── Stat card ─────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, title: str, value: str = "0",
                 color: str = "#00d4ff", subtitle: str = ""):
        super().__init__()
        self.setFixedWidth(140)
        self.setStyleSheet(f"""
            QFrame {{
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 4px;
            }}
            QFrame:hover {{ border-color: {color}44; }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(1)
        layout.setContentsMargins(14, 10, 14, 10)

        self._val = QLabel(value)
        self._val.setStyleSheet(
            f"color:{color}; font-size:30px; font-weight:bold; "
            f"font-family:Consolas; border:none;")
        self._val.setAlignment(Qt.AlignCenter)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            "color:#7d8590; font-size:9px; font-family:Consolas; border:none;")
        self._title.setAlignment(Qt.AlignCenter)

        layout.addWidget(self._val)
        layout.addWidget(self._title)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(
                "color:#3d4450; font-size:8px; font-family:Consolas; border:none;")
            sub.setAlignment(Qt.AlignCenter)
            layout.addWidget(sub)

    def set_value(self, v):
        self._val.setText(str(v))


# ── Drop zone widget ──────────────────────────────────────────────────────────
class DropZone(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._idle_style = """
            QLabel {
                color: #3d4450;
                font-size: 13px;
                padding: 14px;
                border: 2px dashed #21262d;
                margin: 12px 16px 4px 16px;
                background: transparent;
                border-radius: 4px;
            }
        """
        self._hover_style = """
            QLabel {
                color: #00d4ff;
                font-size: 13px;
                padding: 14px;
                border: 2px dashed #00d4ff;
                margin: 12px 16px 4px 16px;
                background: #0d2026;
                border-radius: 4px;
            }
        """
        self.setAlignment(Qt.AlignCenter)
        self.setText(
            "⬇   Drag & drop images or folders here  "
            "—  or use the toolbar above")
        self.setStyleSheet(self._idle_style)

    def set_hover(self, state: bool):
        self.setStyleSheet(self._hover_style if state else self._idle_style)


# ── Main window ───────────────────────────────────────────────────────────────
class ForensiXDashboard(QMainWindow):

    SUPPORTED = {".jpg", ".jpeg", ".png", ".tiff", ".tif",
                 ".bmp", ".webp", ".heic"}

    def __init__(self):
        super().__init__()
        # Engines
        self.evidence_manager = EvidenceManager()
        self.live_map_engine  = LiveMapEngine()
        self.timeline_engine  = TimelineEngine()
        self.report_generator = ReportGenerator()
        self.heatmap_engine   = HeatmapEngine()

        self.all_evidence: list = []
        self.worker: IngestWorker = None

        self._init_window()
        self._init_style()
        self._init_toolbar()
        self._init_central()
        self._init_statusbar()
        self.setAcceptDrops(True)
        self._refresh_stats()

        # Auto-refresh timer (every 30 s while idle)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_stats)
        self._timer.start(30_000)

    # ── Window setup ─────────────────────────────────────────────────────────
    def _init_window(self):
        self.setWindowTitle("ForensiX  —  Digital Forensics Suite  v1.0")
        self.setMinimumSize(1280, 800)
        self.resize(1500, 920)

    def _init_style(self):
        self.setStyleSheet(STYLE)

    # ── Toolbar ───────────────────────────────────────────────────────────────
    def _init_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setIconSize(QSize(14, 14))
        tb.setObjectName("MainToolbar")

        def btn(text, tip, cb, danger=False):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(cb)
            b.setFixedHeight(28)
            if danger:
                b.setObjectName("danger")
            return b

        tb.addWidget(btn("📂  Add Images",  "Import image files", self.open_files))
        tb.addWidget(btn("📁  Add Folder",  "Import entire folder", self.open_folder))
        tb.addSeparator()
        tb.addWidget(btn("🗺  Refresh Map", "Regenerate live map", self.refresh_map))
        tb.addWidget(btn("🔥  Heatmap",     "Generate density heatmap", self.generate_heatmap))
        tb.addSeparator()
        tb.addWidget(btn("📄  Export PDF",  "Generate forensic PDF report", self.export_report))
        tb.addSeparator()
        tb.addWidget(btn("🗑  Clear All",   "Remove all evidence", self.clear_all, danger=True))

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

        # Progress
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedWidth(180)
        self.prog_bar.setFixedHeight(6)
        self.prog_bar.setVisible(False)
        tb.addWidget(self.prog_bar)

        self.prog_lbl = QLabel("  ")
        self.prog_lbl.setStyleSheet("color:#7d8590; font-size:10px; min-width:220px;")
        tb.addWidget(self.prog_lbl)

    # ── Central widget ────────────────────────────────────────────────────────
    def _init_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Stats bar ─────────────────────────────────────────────────────────
        stats_bar = QWidget()
        stats_bar.setStyleSheet(
            "background:#161b22; border-bottom:1px solid #30363d;")
        stats_layout = QHBoxLayout(stats_bar)
        stats_layout.setContentsMargins(14, 8, 14, 8)
        stats_layout.setSpacing(10)

        self.sc_total    = StatCard("TOTAL IMAGES",   "0", "#00d4ff")
        self.sc_gps      = StatCard("WITH GPS",       "0", "#3fb950")
        self.sc_anomaly  = StatCard("ANOMALIES",      "0", "#f78166")
        self.sc_critical = StatCard("CRITICAL",       "0", "#ff2222")
        self.sc_high     = StatCard("HIGH",           "0", "#ff7b00")

        for card in [self.sc_total, self.sc_gps, self.sc_anomaly,
                     self.sc_critical, self.sc_high]:
            stats_layout.addWidget(card)

        stats_layout.addStretch()

        brand = QLabel("⬡  ForensiX  DFIR")
        brand.setStyleSheet(
            "color:#00d4ff; font-size:14px; font-weight:bold; "
            "letter-spacing:1px;")
        stats_layout.addWidget(brand)
        main_layout.addWidget(stats_bar)

        # ── Drop zone ─────────────────────────────────────────────────────────
        self.drop_zone = DropZone()
        main_layout.addWidget(self.drop_zone)

        # ── Tabs ──────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.map_view       = LiveMapView()
        self.metadata_panel = MetadataPanel()
        self.timeline_view  = TimelineView()
        self.anomaly_panel  = AnomalyPanel()

        self.tabs.addTab(self.map_view,       "🗺   Live Map")
        self.tabs.addTab(self.metadata_panel, "📋   Evidence & Metadata")
        self.tabs.addTab(self.timeline_view,  "📅   Timeline")
        self.tabs.addTab(self.anomaly_panel,  "⚠️   Anomalies")
        main_layout.addWidget(self.tabs)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _init_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage(
            "ForensiX ready  |  Drag & drop images to begin forensic analysis")

    # ── Drag & drop ───────────────────────────────────────────────────────────
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_zone.set_hover(True)

    def dragLeaveEvent(self, event):
        self.drop_zone.set_hover(False)

    def dropEvent(self, event):
        self.drop_zone.set_hover(False)
        paths = self._collect_paths_from_urls(event.mimeData().urls())
        if paths:
            self._ingest(paths)
        else:
            self.statusBar().showMessage(
                "No supported image files found in dropped items")

    def _collect_paths_from_urls(self, urls) -> list:
        paths = []
        for url in urls:
            fp = url.toLocalFile()
            if os.path.isdir(fp):
                for root, _, files in os.walk(fp):
                    for f in files:
                        if os.path.splitext(f)[1].lower() in self.SUPPORTED:
                            paths.append(os.path.join(root, f))
            elif os.path.splitext(fp)[1].lower() in self.SUPPORTED:
                paths.append(fp)
        return paths

    # ── File dialogs ──────────────────────────────────────────────────────────
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Images", "",
            "Images (*.jpg *.jpeg *.png *.tiff *.tif *.bmp *.webp *.heic)")
        if files:
            self._ingest(files)

    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return
        paths = []
        for root, _, files in os.walk(folder):
            for f in files:
                if os.path.splitext(f)[1].lower() in self.SUPPORTED:
                    paths.append(os.path.join(root, f))
        if paths:
            self._ingest(paths)
        else:
            self.statusBar().showMessage(
                "No supported image files found in the selected folder")

    # ── Ingestion pipeline ────────────────────────────────────────────────────
    def _ingest(self, filepaths: list):
        if self.worker and self.worker.isRunning():
            self.statusBar().showMessage(
                "⏳  Processing in progress — please wait")
            return

        self.drop_zone.hide()
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)

        self.worker = IngestWorker(filepaths)
        self.worker.progress.connect(self._on_progress)
        self.worker.result.connect(self._on_result)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(
            lambda msg: logger.warning(f"Ingest: {msg}"))
        self.worker.start()

        self.statusBar().showMessage(
            f"⚙  Ingesting {len(filepaths)} image(s)…")

    def _on_progress(self, pct: int, filename: str):
        self.prog_bar.setValue(pct)
        self.prog_lbl.setText(f"  {filename[:50]}")

    def _on_result(self, result: dict):
        self.all_evidence.append(result)
        self.metadata_panel.add_evidence(result)
        anomalies = result.get("anomalies", [])
        if anomalies:
            self.anomaly_panel.add_anomalies(
                result["metadata"].get("filename", "?"), anomalies)

    def _on_finished(self, success: int, errors: int):
        self.prog_bar.setVisible(False)
        self.prog_lbl.setText("")
        self._refresh_stats()
        self._update_timeline()
        self.refresh_map()

        msg = (f"✓  {success} image(s) ingested"
               + (f"  |  ⚠ {errors} error(s)" if errors else "")
               + f"  |  {datetime.now().strftime('%H:%M:%S')}")
        self.statusBar().showMessage(msg)

        # Switch to map tab if we have GPS data
        gps_points = self.evidence_manager.get_gps_points()
        if gps_points:
            self.tabs.setCurrentIndex(0)

    # ── Stats refresh ─────────────────────────────────────────────────────────
    def _refresh_stats(self):
        s = self.evidence_manager.get_stats()
        self.sc_total.set_value(s.get("total_images", 0))
        self.sc_gps.set_value(s.get("with_gps", 0))
        self.sc_anomaly.set_value(s.get("total_anomalies", 0))
        self.sc_critical.set_value(s.get("critical_anomalies", 0))
        self.sc_high.set_value(s.get("high_anomalies", 0))

    # ── Timeline ──────────────────────────────────────────────────────────────
    def _update_timeline(self):
        data = [r["metadata"] for r in self.all_evidence]
        timeline = self.timeline_engine.build_timeline(data)
        # Attach anomaly counts
        for item in timeline:
            fp = item.get("filepath", "")
            for ev in self.all_evidence:
                if ev["metadata"].get("filepath") == fp:
                    item["anomalies"] = ev.get("anomalies", [])
                    break
        self.timeline_view.load_timeline(timeline)

    # ── Map ───────────────────────────────────────────────────────────────────
    def refresh_map(self):
        gps_points = self.evidence_manager.get_gps_points()
        points = []
        # Build anomaly count lookup
        anomaly_counts = {}
        for ev in self.all_evidence:
            fname = ev["metadata"].get("filename", "")
            anomaly_counts[fname] = len(ev.get("anomalies", []))

        for p in gps_points:
            if p.get("lat") and p.get("lon"):
                fname = p.get("filename", "")
                points.append({
                    "lat":           p["lat"],
                    "lon":           p["lon"],
                    "filename":      fname,
                    "timestamp":     p.get("timestamp_original", ""),
                    "camera":        (f"{p.get('camera_make','')} "
                                      f"{p.get('camera_model','')}").strip(),
                    "anomaly_count": anomaly_counts.get(fname, 0)
                })

        map_path = self.live_map_engine.generate_map(
            points, show_heatmap=False, show_paths=True)
        self.map_view.load_map(map_path)
        self.statusBar().showMessage(
            f"🗺  Map updated  |  {len(points)} GPS point(s) plotted")

    # ── Heatmap ───────────────────────────────────────────────────────────────
    def generate_heatmap(self):
        gps_points = self.evidence_manager.get_gps_points()
        pts = [{"lat": p["lat"], "lon": p["lon"]}
               for p in gps_points if p.get("lat") and p.get("lon")]
        if len(pts) < 2:
            self.statusBar().showMessage(
                "⚠  Need at least 2 GPS points to generate a heatmap")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("exports", exist_ok=True)
        out = os.path.join("exports", f"heatmap_{ts}.png")
        result = self.heatmap_engine.generate_density_map(pts, out)

        if result:
            # Also refresh the folium map with heatmap layer
            map_pts = [{"lat": p["lat"], "lon": p["lon"],
                        "filename": "", "timestamp": "",
                        "camera": "", "anomaly_count": 0}
                       for p in pts]
            map_path = self.live_map_engine.generate_map(
                map_pts, show_heatmap=True)
            self.map_view.load_map(map_path)
            self.statusBar().showMessage(
                f"🔥  Heatmap saved: {result}  |  Map updated with density overlay")
        else:
            self.statusBar().showMessage(
                "⚠  Heatmap generation failed — install matplotlib")

    # ── Report ────────────────────────────────────────────────────────────────
    def export_report(self):
        os.makedirs("reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default = os.path.join("reports", f"forensix_report_{ts}.pdf")

        path, _ = QFileDialog.getSaveFileName(
            self, "Save Forensic Report", default, "PDF Files (*.pdf)")
        if not path:
            return

        self.statusBar().showMessage("📄  Generating forensic report…")
        QApplication.processEvents()

        evidence_list = self.evidence_manager.get_all_evidence()
        anomalies     = self.evidence_manager.get_anomalies()
        stats         = self.evidence_manager.get_stats()

        out = self.report_generator.generate(
            evidence_list, anomalies, stats, path,
            f"ForensiX Investigation — {datetime.now().strftime('%Y-%m-%d')}")

        self.statusBar().showMessage(f"✓  Report saved: {out}")
        QMessageBox.information(
            self, "Report Generated",
            f"Forensic report saved successfully:\n\n{out}")

    # ── Clear all ─────────────────────────────────────────────────────────────
    def clear_all(self):
        reply = QMessageBox.question(
            self, "Clear All Evidence",
            "This will remove ALL evidence from the database and reset the view.\n"
            "This action cannot be undone.\n\nContinue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.evidence_manager.clear_all()
        self.all_evidence.clear()

        # Reset panels
        self.metadata_panel._evidence_data.clear()
        self.metadata_panel.evidence_table.setRowCount(0)
        self.metadata_panel.detail_tree.clear()

        self.anomaly_panel.tree.clear()
        self.anomaly_panel._anomaly_data.clear()
        self.anomaly_panel._counts = {
            "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        self.anomaly_panel._update_badges()

        self.timeline_view.load_timeline([])

        self.map_view._show_placeholder()

        self.drop_zone.show()
        self._refresh_stats()
        self.statusBar().showMessage("All evidence cleared")
