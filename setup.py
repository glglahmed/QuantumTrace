#!/usr/bin/env python3
"""
ForensiX — Setup & Dependency Checker
Run:  python setup.py
"""
import subprocess
import sys
import os

REQUIRED = [
    ("PyQt5",              "PyQt5>=5.15.9"),
    ("PIL",                "Pillow>=10.0.0"),
    ("cv2",                "opencv-python>=4.8.0"),
    ("exifread",           "exifread>=3.0.0"),
    ("piexif",             "piexif>=1.1.3"),
    ("folium",             "folium>=0.14.0"),
    ("geopy",              "geopy>=2.4.0"),
    ("branca",             "branca>=0.6.0"),
    ("matplotlib",         "matplotlib>=3.7.0"),
    ("plotly",             "plotly>=5.15.0"),
    ("reportlab",          "reportlab>=4.0.0"),
    ("pandas",             "pandas>=2.0.0"),
    ("numpy",              "numpy>=1.24.0"),
    ("requests",           "requests>=2.31.0"),
]

OPTIONAL = [
    ("PyQt5.QtWebEngineWidgets", "PyQtWebEngine>=5.15.6",
     "Required for in-app interactive map rendering"),
]


def check_import(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def pip_install(package: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package],
        capture_output=True, text=True)
    return result.returncode == 0


def main():
    print("=" * 60)
    print("  ForensiX — Dependency Setup")
    print("=" * 60)
    print()

    # Create output dirs
    for d in ["database", "reports", "exports", "temp", "sample_images"]:
        os.makedirs(d, exist_ok=True)
    print("  ✓  Output directories created")
    print()

    # Required packages
    print("  Checking required packages...")
    missing = []
    for module, pkg in REQUIRED:
        if check_import(module):
            print(f"    ✓  {module:<30} installed")
        else:
            print(f"    ✗  {module:<30} MISSING  → installing {pkg}...")
            if pip_install(pkg):
                print(f"    ✓  {pkg} installed successfully")
            else:
                missing.append(pkg)
                print(f"    ✗  Failed to install {pkg}")

    print()

    # Optional packages
    print("  Checking optional packages...")
    for module, pkg, note in OPTIONAL:
        if check_import(module):
            print(f"    ✓  {module:<40} installed")
        else:
            print(f"    ○  {module:<40} not installed")
            print(f"         ({note})")
            ans = input(f"         Install {pkg}? [y/N]: ").strip().lower()
            if ans == "y":
                if pip_install(pkg):
                    print(f"    ✓  {pkg} installed")
                else:
                    print(f"    ✗  Failed — try: pip install {pkg}")

    print()

    if missing:
        print(f"  ⚠  {len(missing)} package(s) failed to install:")
        for p in missing:
            print(f"     pip install {p}")
        print()
    else:
        print("  ✓  All required packages ready")

    print()
    print("  Generating sample dataset...")
    try:
        import generate_sample_dataset
        generate_sample_dataset.generate()
    except Exception as e:
        print(f"  ○  Sample generation skipped: {e}")

    print()
    print("=" * 60)
    print("  Setup complete.  Run:  python main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
