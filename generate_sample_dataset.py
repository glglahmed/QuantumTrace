#!/usr/bin/env python3
"""
ForensiX — Sample Dataset Generator
Creates synthetic JPEG images with embedded EXIF and GPS metadata for testing.
Run:  python generate_sample_dataset.py
Output: sample_images/  (10 test images)
"""

import os
import struct
import io
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Attempt to use Pillow + piexif for rich EXIF.
# Falls back to raw JFIF if neither is available.
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW = True
except ImportError:
    PILLOW = False

try:
    import piexif
    PIEXIF = True
except ImportError:
    PIEXIF = False


OUTPUT_DIR = "sample_images"

# 10 realistic GPS locations around the world
LOCATIONS = [
    ("Cairo, Egypt",         30.0444,  31.2357),
    ("London, UK",           51.5074,  -0.1278),
    ("New York, USA",        40.7128, -74.0060),
    ("Tokyo, Japan",         35.6762, 139.6503),
    ("Sydney, Australia",   -33.8688, 151.2093),
    ("Paris, France",        48.8566,   2.3522),
    ("Dubai, UAE",           25.2048,  55.2708),
    ("São Paulo, Brazil",   -23.5505, -46.6333),
    ("Moscow, Russia",       55.7558,  37.6173),
    ("Cape Town, S. Africa", -33.9249,  18.4241),
]

CAMERAS = [
    ("Apple",   "iPhone 14 Pro"),
    ("Samsung", "Galaxy S23"),
    ("Google",  "Pixel 7"),
    ("Canon",   "EOS R5"),
    ("Nikon",   "Z6 II"),
]

SOFTWARE_OPTIONS = [
    None, None, None,   # most images untouched
    "Adobe Photoshop 24.0",
    "GIMP 2.10",
    None,
    "Snapseed 2.19",
    None, None, None,
]

COLORS = [
    "#1a3a5c", "#2d5a27", "#5c1a1a", "#2d2d5a",
    "#5a4a1a", "#1a5a5a", "#4a1a5a", "#1a4a3a",
    "#5a3a1a", "#3a1a5a",
]


def dd_to_dms_rational(dd: float):
    """Convert decimal degrees to DMS as piexif rationals."""
    dd = abs(dd)
    d = int(dd)
    m = int((dd - d) * 60)
    s = (dd - d - m / 60) * 3600
    return [(d, 1), (m, 1), (int(s * 1000), 1000)]


def make_image_piexif(idx: int, loc_name: str, lat: float, lon: float,
                      camera_make: str, camera_model: str,
                      software: str, ts: datetime) -> bytes:
    """Create JPEG bytes with full EXIF using Pillow + piexif."""
    # --- Draw image ---
    img = Image.new("RGB", (800, 600), color=COLORS[idx % len(COLORS)])
    draw = ImageDraw.Draw(img)

    # Grid lines
    for x in range(0, 800, 80):
        draw.line([(x, 0), (x, 600)], fill="#ffffff22", width=1)
    for y in range(0, 600, 60):
        draw.line([(0, y), (800, y)], fill="#ffffff22", width=1)

    # Text overlay
    draw.rectangle([20, 20, 780, 200], fill="#00000088")
    draw.text((40, 35),  f"ForensiX Sample #{idx+1:02d}", fill="#00d4ff")
    draw.text((40, 75),  f"Location : {loc_name}",        fill="#c9d1d9")
    draw.text((40, 105), f"GPS      : {lat:.4f}, {lon:.4f}", fill="#3fb950")
    draw.text((40, 135), f"Camera   : {camera_make} {camera_model}", fill="#c9d1d9")
    draw.text((40, 165), f"Captured : {ts.strftime('%Y-%m-%d %H:%M:%S')}", fill="#c9d1d9")
    if software:
        draw.rectangle([20, 210, 400, 250], fill="#ff000033")
        draw.text((30, 218), f"⚠ Software: {software}", fill="#f78166")

    # --- Build EXIF ---
    lat_ref = "N" if lat >= 0 else "S"
    lon_ref = "E" if lon >= 0 else "W"

    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef:  lat_ref.encode(),
        piexif.GPSIFD.GPSLatitude:     dd_to_dms_rational(lat),
        piexif.GPSIFD.GPSLongitudeRef: lon_ref.encode(),
        piexif.GPSIFD.GPSLongitude:    dd_to_dms_rational(lon),
        piexif.GPSIFD.GPSAltitudeRef:  0,
        piexif.GPSIFD.GPSAltitude:     (int(random.uniform(0, 500) * 100), 100),
    }

    ts_str = ts.strftime("%Y:%m:%d %H:%M:%S").encode()

    zeroth_ifd = {
        piexif.ImageIFD.Make:             camera_make.encode(),
        piexif.ImageIFD.Model:            camera_model.encode(),
        piexif.ImageIFD.DateTime:         ts_str,
        piexif.ImageIFD.XResolution:      (72, 1),
        piexif.ImageIFD.YResolution:      (72, 1),
        piexif.ImageIFD.ResolutionUnit:   2,
        piexif.ImageIFD.Orientation:      1,
    }
    if software:
        zeroth_ifd[piexif.ImageIFD.Software] = software.encode()

    exif_ifd = {
        piexif.ExifIFD.DateTimeOriginal:  ts_str,
        piexif.ExifIFD.DateTimeDigitized: ts_str,
        piexif.ExifIFD.ExposureTime:      (1, random.choice([30, 60, 125, 250, 500])),
        piexif.ExifIFD.FNumber:           (random.choice([18, 20, 28, 40]), 10),
        piexif.ExifIFD.ISOSpeedRatings:   random.choice([100, 200, 400, 800, 1600]),
        piexif.ExifIFD.FocalLength:       (random.choice([24, 35, 50, 85, 200]), 1),
        piexif.ExifIFD.Flash:             0,
        piexif.ExifIFD.ColorSpace:        1,
        piexif.ExifIFD.PixelXDimension:   800,
        piexif.ExifIFD.PixelYDimension:   600,
    }

    exif_dict = {
        "0th":  zeroth_ifd,
        "Exif": exif_ifd,
        "GPS":  gps_ifd,
    }

    try:
        exif_bytes = piexif.dump(exif_dict)
    except Exception:
        exif_bytes = b""

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92, exif=exif_bytes)
    return buf.getvalue()


def make_image_minimal(idx: int, loc_name: str, lat: float, lon: float,
                       camera_make: str, camera_model: str,
                       software: str, ts: datetime) -> bytes:
    """
    Fallback: plain white JPEG with no EXIF (Pillow available, piexif not).
    """
    img = Image.new("RGB", (400, 300), color=COLORS[idx % len(COLORS)])
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), f"Sample #{idx+1:02d} - {loc_name}", fill="#ffffff")
    draw.text((10, 40), f"{lat:.4f}, {lon:.4f}", fill="#00d4ff")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def make_minimal_jpeg(idx: int) -> bytes:
    """
    Absolute fallback: tiny valid JPEG (no Pillow at all).
    16×16 solid-color JPEG, pure Python struct approach.
    """
    # Minimal JFIF JPEG for a single-color 1×1 image
    # Using a hard-coded 1x1 JPEG (100 bytes)
    TINY_JPEG = bytes([
        0xFF,0xD8,0xFF,0xE0,0x00,0x10,0x4A,0x46,0x49,0x46,0x00,0x01,
        0x01,0x00,0x00,0x01,0x00,0x01,0x00,0x00,0xFF,0xDB,0x00,0x43,
        0x00,0x08,0x06,0x06,0x07,0x06,0x05,0x08,0x07,0x07,0x07,0x09,
        0x09,0x08,0x0A,0x0C,0x14,0x0D,0x0C,0x0B,0x0B,0x0C,0x19,0x12,
        0x13,0x0F,0x14,0x1D,0x1A,0x1F,0x1E,0x1D,0x1A,0x1C,0x1C,0x20,
        0x24,0x2E,0x27,0x20,0x22,0x2C,0x23,0x1C,0x1C,0x28,0x37,0x29,
        0x2C,0x30,0x31,0x34,0x34,0x34,0x1F,0x27,0x39,0x3D,0x38,0x32,
        0x3C,0x2E,0x33,0x34,0x32,0xFF,0xC0,0x00,0x0B,0x08,0x00,0x01,
        0x00,0x01,0x01,0x01,0x11,0x00,0xFF,0xC4,0x00,0x1F,0x00,0x00,
        0x01,0x05,0x01,0x01,0x01,0x01,0x01,0x01,0x00,0x00,0x00,0x00,
        0x00,0x00,0x00,0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,
        0x09,0x0A,0x0B,0xFF,0xC4,0x00,0xB5,0x10,0x00,0x02,0x01,0x03,
        0x03,0x02,0x04,0x03,0x05,0x05,0x04,0x04,0x00,0x00,0x01,0x7D,
        0x01,0x02,0x03,0x00,0x04,0x11,0x05,0x12,0x21,0x31,0x41,0x06,
        0x13,0x51,0x61,0x07,0x22,0x71,0x14,0x32,0x81,0x91,0xA1,0x08,
        0x23,0x42,0xB1,0xC1,0x15,0x52,0xD1,0xF0,0x24,0x33,0x62,0x72,
        0x82,0x09,0x0A,0x16,0x17,0x18,0x19,0x1A,0x25,0x26,0x27,0x28,
        0x29,0x2A,0x34,0x35,0x36,0x37,0x38,0x39,0x3A,0x43,0x44,0x45,
        0x46,0x47,0x48,0x49,0x4A,0x53,0x54,0x55,0x56,0x57,0x58,0x59,
        0x5A,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6A,0x73,0x74,0x75,
        0x76,0x77,0x78,0x79,0x7A,0x83,0x84,0x85,0x86,0x87,0x88,0x89,
        0x8A,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9A,0xA2,0xA3,
        0xA4,0xA5,0xA6,0xA7,0xA8,0xA9,0xAA,0xB2,0xB3,0xB4,0xB5,0xB6,
        0xB7,0xB8,0xB9,0xBA,0xC2,0xC3,0xC4,0xC5,0xC6,0xC7,0xC8,0xC9,
        0xCA,0xD2,0xD3,0xD4,0xD5,0xD6,0xD7,0xD8,0xD9,0xDA,0xE1,0xE2,
        0xE3,0xE4,0xE5,0xE6,0xE7,0xE8,0xE9,0xEA,0xF1,0xF2,0xF3,0xF4,
        0xF5,0xF6,0xF7,0xF8,0xF9,0xFA,0xFF,0xDA,0x00,0x08,0x01,0x01,
        0x00,0x00,0x3F,0x00,0xFB,0xD4,0xFF,0xD9
    ])
    return TINY_JPEG


def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_time = datetime(2024, 3, 15, 8, 0, 0)

    manifest_lines = ["# ForensiX Sample Dataset Manifest", ""]

    print(f"ForensiX — Generating {len(LOCATIONS)} sample images in '{OUTPUT_DIR}/'")
    print("-" * 60)

    for i, (loc_name, lat, lon) in enumerate(LOCATIONS):
        make, model = CAMERAS[i % len(CAMERAS)]
        software    = SOFTWARE_OPTIONS[i % len(SOFTWARE_OPTIONS)]
        ts          = base_time + timedelta(hours=i * 4 + random.randint(0, 60))

        filename = (f"sample_{i+1:02d}_"
                    f"{loc_name.split(',')[0].lower().replace(' ', '_')}.jpg")
        filepath = os.path.join(OUTPUT_DIR, filename)

        # Special cases to showcase anomaly detection
        if i == 3:
            # Future timestamp
            ts = datetime(2099, 1, 1, 12, 0, 0)
        if i == 7:
            # Null Island GPS
            lat, lon = 0.0, 0.0

        # Generate bytes
        try:
            if PILLOW and PIEXIF:
                data = make_image_piexif(i, loc_name, lat, lon,
                                         make, model, software, ts)
                method = "Pillow+piexif (full EXIF)"
            elif PILLOW:
                data = make_image_minimal(i, loc_name, lat, lon,
                                          make, model, software, ts)
                method = "Pillow only (no EXIF)"
            else:
                data = make_minimal_jpeg(i)
                method = "raw JFIF fallback"
        except Exception as e:
            data = make_minimal_jpeg(i)
            method = f"fallback (error: {e})"

        with open(filepath, "wb") as f:
            f.write(data)

        size_kb = len(data) / 1024
        flag = ""
        if software:
            flag = "  [EDITED]"
        if i == 3:
            flag = "  [FUTURE TIMESTAMP]"
        if i == 7:
            flag = "  [NULL ISLAND GPS]"

        print(f"  [{i+1:02d}] {filename:<52} {size_kb:6.1f} KB  {flag}")
        manifest_lines.append(
            f"{i+1:02d} | {filename} | {loc_name} | "
            f"{lat:.4f},{lon:.4f} | {ts.strftime('%Y-%m-%d %H:%M')} | "
            f"{make} {model} | {software or 'Original'}")

    # Write manifest
    manifest_path = os.path.join(OUTPUT_DIR, "MANIFEST.txt")
    with open(manifest_path, "w") as f:
        f.write("\n".join(manifest_lines))

    print("-" * 60)
    print(f"  ✓  {len(LOCATIONS)} images written to '{OUTPUT_DIR}/'")
    print(f"  ✓  Manifest: {manifest_path}")
    print()
    print("  Anomaly showcase images:")
    print("    #04 — Future timestamp (2099)")
    print("    #08 — Null Island GPS (0.0, 0.0)")
    print("    #04,#06,#07 — Editing software embedded")
    print()
    print("  Drag the 'sample_images/' folder into ForensiX to test.")


if __name__ == "__main__":
    generate()
