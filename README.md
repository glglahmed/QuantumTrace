# ForensiX — Digital Image Metadata & Geolocation Forensics Suite

> A professional DFIR (Digital Forensics & Incident Response) platform for image
> metadata extraction, GPS intelligence, timeline reconstruction, anomaly detection,
> live geospatial visualization, and forensic reporting.

---

## Features

| Module | Description |
|--------|-------------|
| **EXIF Forensics** | Full metadata extraction — camera, timestamps, GPS, software tags |
| **GPS Intelligence** | DMS→Decimal conversion, reverse geocoding, impossible travel detection |
| **Live Interactive Map** | Folium map with markers, clustering, movement paths, heatmap overlay |
| **Timeline Reconstruction** | Chronological sorting, movement path, time-gap detection |
| **Anomaly Detection** | 15+ rule-based checks: missing EXIF, editing software, timestamp anomalies |
| **Validation Engine** | File integrity, GPS range, timestamp, EXIF completeness checks |
| **Chain of Custody** | SHA-256 + MD5 hashing, immutable SQLite audit log |
| **Drag & Drop Ingestion** | Drop images or entire folders — auto-processes the full pipeline |
| **Forensic PDF Reports** | Full case reports via ReportLab |
| **Dark DFIR UI** | Professional dark theme built on PyQt5 |

---

## Installation

```bash
# 1. Clone or extract the project
cd forensix

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Enable in-app map rendering
pip install PyQtWebEngine
```

### Platform Notes

- **Windows**: Ensure Python 3.10+ is on PATH
- **macOS**: `brew install python-tk` may be needed for some Qt builds
- **Linux**: `sudo apt install python3-pyqt5 python3-pyqt5.qtwebengine`

---

## Run

```bash
python main.py
```

---

## Usage

1. Launch — the splash screen appears while engines initialize
2. **Drag & drop** images or folders onto the window (or use toolbar buttons)
3. ForensiX auto-runs the full pipeline:
   - EXIF extraction
   - SHA-256 / MD5 hashing
   - Anomaly detection
   - Validation
   - GPS coordinate parsing
   - Database storage
4. Explore the four tabs:
   - **🗺 Live Map** — GPS evidence plotted on interactive map
   - **📋 Evidence & Metadata** — Full EXIF detail tree per image
   - **📅 Timeline** — Chronological event list
   - **⚠️ Anomalies** — Severity-grouped anomaly report
5. **Export PDF** — Full forensic report with evidence table, anomalies, chain of custody

---

## Supported Formats

`JPG` · `JPEG` · `PNG` · `TIFF` · `BMP` · `WEBP` · `HEIC`

---

## Project Structure

```
forensix/
├── main.py                     Entry point / splash
├── requirements.txt
├── README.md
├── core/
│   ├── exif_engine.py          EXIF extraction (Pillow + exifread)
│   ├── gps_decoder.py          GPS decode, Haversine, reverse geocode
│   ├── anomaly_detector.py     Rule-based anomaly detection
│   ├── validation_engine.py    Forensic correctness validation
│   ├── timeline_engine.py      Chronological reconstruction
│   ├── live_map_engine.py      Folium interactive map generation
│   ├── heatmap_engine.py       Matplotlib density heatmap
│   ├── hash_engine.py          SHA-256 / MD5 + chain of custody log
│   ├── evidence_manager.py     SQLite 5-table evidence store
│   ├── report_generator.py     ReportLab PDF forensic reports
│   └── correlation_engine.py   Time + location evidence correlation
├── ui/
│   ├── dashboard.py            Main PyQt5 window + drag & drop
│   ├── live_map_view.py        WebEngine map display panel
│   ├── metadata_panel.py       Evidence table + EXIF detail tree
│   ├── timeline_view.py        Chronological evidence list
│   ├── anomaly_panel.py        Severity-badged anomaly display
│   └── image_viewer.py         Zoomable image viewer
├── database/                   SQLite evidence.db (auto-created)
├── reports/                    PDF output directory
├── exports/                    Heatmap image exports
└── temp/                       Folium map HTML files
```

---

## Database Schema

| Table | Contents |
|-------|----------|
| `evidence` | File metadata, SHA-256, GPS, camera, timestamps |
| `anomalies` | Type, severity, field, detail per evidence item |
| `validation_results` | Per-check pass/warn/fail results |
| `custody_log` | Immutable chain-of-custody action log |
| `gps_points` | Extracted GPS coordinates |

---

## Dependencies

```
PyQt5              GUI framework
PyQtWebEngine      In-app map rendering (optional)
Pillow             Image opening + EXIF parsing
exifread           Deep EXIF tag reading
piexif             EXIF read/write
folium             Interactive HTML maps
geopy              Reverse geocoding
branca             Folium HTML templates
matplotlib         Heatmap / density plots
plotly             Interactive data visualization
reportlab          PDF report generation
pandas             Data manipulation
numpy              Numerical operations
requests           HTTP requests
```

---

## License

ForensiX is intended for legitimate digital forensics investigation purposes only.
All evidence is processed in read-only mode. Chain of custody is maintained
throughout the investigation lifecycle.
