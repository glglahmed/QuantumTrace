#!/usr/bin/env python3
"""
ForensiX - Advanced Digital Image Metadata & Geolocation Forensics Suite
Main entry point
"""

import sys
import os
import logging

# Ensure directories exist
for d in ["database", "reports", "exports", "temp"]:
    os.makedirs(d, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("forensix.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ForensiX")

from PyQt5.QtWidgets import QApplication, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor, QPainter, QFont

from ui.dashboard import ForensiXDashboard


def create_splash():
    pixmap = QPixmap(600, 350)
    pixmap.fill(QColor("#0d1117"))
    painter = QPainter(pixmap)

    painter.setFont(QFont("Consolas", 40, QFont.Bold))
    painter.setPen(QColor("#00d4ff"))
    painter.drawText(0, 80, 600, 80, Qt.AlignCenter, "ForensiX")

    painter.setFont(QFont("Consolas", 11))
    painter.setPen(QColor("#7d8590"))
    painter.drawText(0, 150, 600, 40, Qt.AlignCenter,
                     "Digital Image Metadata & Geolocation Forensics Suite")

    painter.setFont(QFont("Consolas", 9))
    painter.setPen(QColor("#3d4450"))
    painter.drawText(0, 200, 600, 30, Qt.AlignCenter, "v1.0.0  |  DFIR Platform")

    painter.setFont(QFont("Consolas", 9))
    painter.setPen(QColor("#00d4ff"))
    painter.drawText(0, 310, 600, 30, Qt.AlignCenter, "Initializing forensic engines...")

    painter.end()
    return QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ForensiX")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ForensiX DFIR")
    app.setStyle("Fusion")

    splash = create_splash()
    splash.show()
    app.processEvents()

    window = ForensiXDashboard()

    def show_main():
        splash.finish(window)
        window.show()

    QTimer.singleShot(2000, show_main)
    logger.info("ForensiX launched successfully")
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
