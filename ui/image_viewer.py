"""
Image Viewer - Zoomable image display with metadata overlay
"""
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QSizePolicy, QSlider
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QColor

logger = logging.getLogger(__name__)


class ImageViewer(QWidget):

    def __init__(self):
        super().__init__()
        self._zoom = 1.0
        self._pixmap = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet(
            "background:#161b22; border-bottom:1px solid #30363d;")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(12, 6, 12, 6)

        self.filename_lbl = QLabel("No image selected")
        self.filename_lbl.setStyleSheet(
            "color:#00d4ff; font-size:11px; font-weight:bold;")
        tb_layout.addWidget(self.filename_lbl)
        tb_layout.addStretch()

        self.zoom_lbl = QLabel("100%")
        self.zoom_lbl.setStyleSheet("color:#7d8590; font-size:10px;")
        tb_layout.addWidget(self.zoom_lbl)
        layout.addWidget(toolbar)

        # Image area
        self.scroll = QScrollArea()
        self.scroll.setStyleSheet(
            "QScrollArea { background:#0d1117; border:none; }")
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setWidgetResizable(False)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background:#0d1117;")
        self.image_label.setText(
            '<div style="color:#3d4450;font-family:monospace;font-size:14px;">'
            '🖼  Select an image from the Evidence panel</div>')
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll)

    def load_image(self, filepath: str, filename: str = ""):
        try:
            pixmap = QPixmap(filepath)
            if pixmap.isNull():
                self.image_label.setText(
                    f'<div style="color:#f78166;font-family:monospace;">'
                    f'Cannot display: {filename}</div>')
                return
            self._pixmap = pixmap
            self.filename_lbl.setText(filename or filepath)
            self._apply_zoom()
        except Exception as e:
            logger.error(f"Image load error: {e}")

    def _apply_zoom(self):
        if self._pixmap is None:
            return
        w = int(self._pixmap.width() * self._zoom)
        h = int(self._pixmap.height() * self._zoom)
        scaled = self._pixmap.scaled(
            w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())
        self.zoom_lbl.setText(f"{int(self._zoom * 100)}%")

    def wheelEvent(self, event):
        if self._pixmap:
            delta = event.angleDelta().y()
            if delta > 0:
                self._zoom = min(self._zoom * 1.15, 8.0)
            else:
                self._zoom = max(self._zoom / 1.15, 0.05)
            self._apply_zoom()
