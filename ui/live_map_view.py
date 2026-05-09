"""
Live Map View - WebEngine interactive map panel
"""
import os
import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton)
from PyQt5.QtCore import Qt, QUrl

logger = logging.getLogger(__name__)

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    logger.warning("PyQtWebEngine not available — install PyQtWebEngine for in-app maps")


class LiveMapView(QWidget):

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Control bar
        ctrl = QWidget()
        ctrl.setStyleSheet("background:#161b22; border-bottom:1px solid #30363d;")
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(14, 7, 14, 7)

        lbl = QLabel("🗺  LIVE GEOSPATIAL MAP  —  Evidence Locations & Movement Paths")
        lbl.setStyleSheet("color:#00d4ff; font-size:11px; font-weight:bold;")
        ctrl_layout.addWidget(lbl)
        ctrl_layout.addStretch()

        self.status_lbl = QLabel("Awaiting evidence import")
        self.status_lbl.setStyleSheet("color:#7d8590; font-size:10px;")
        ctrl_layout.addWidget(self.status_lbl)

        layout.addWidget(ctrl)

        if WEB_ENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            self.web_view.setStyleSheet("background:#0d1117;")
            layout.addWidget(self.web_view)
            self._show_placeholder()
        else:
            fallback = QLabel(
                "🗺  In-app map requires PyQtWebEngine\n\n"
                "Install with:\n"
                "    pip install PyQtWebEngine\n\n"
                "Maps are still generated as HTML files in the /temp/ folder\n"
                "and can be opened in any web browser."
            )
            fallback.setAlignment(Qt.AlignCenter)
            fallback.setStyleSheet(
                "color:#7d8590; font-size:13px; padding:60px; "
                "background:#161b22; border:1px dashed #30363d; margin:20px;")
            layout.addWidget(fallback)

    def _show_placeholder(self):
        if not WEB_ENGINE_AVAILABLE:
            return
        html = """<!DOCTYPE html>
<html>
<head>
<style>
  body { background:#0d1117; margin:0; display:flex;
         justify-content:center; align-items:center; height:100vh; }
  .container { text-align:center; font-family:monospace; }
  .icon { font-size:64px; margin-bottom:20px; }
  .title { color:#00d4ff; font-size:22px; font-weight:bold; margin-bottom:10px; }
  .sub { color:#7d8590; font-size:13px; line-height:1.8; }
  .pulse { animation:pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
</style>
</head>
<body>
  <div class="container">
    <div class="icon pulse">🗺</div>
    <div class="title">ForensiX Live Map</div>
    <div class="sub">
      Import images with GPS metadata to visualize evidence locations<br>
      Supports: markers · movement paths · clustering · heatmap overlay
    </div>
  </div>
</body>
</html>"""
        self.web_view.setHtml(html)

    def load_map(self, html_path: str):
        if not WEB_ENGINE_AVAILABLE:
            return
        if html_path and os.path.exists(html_path):
            url = QUrl.fromLocalFile(os.path.abspath(html_path))
            self.web_view.load(url)
            self.status_lbl.setText(
                f"Loaded: {os.path.basename(html_path)}")
        else:
            self._show_placeholder()
            self.status_lbl.setText("No map data available")
