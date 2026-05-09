"""
Heatmap Engine - Geospatial density and movement visualization
"""
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class HeatmapEngine:

    def generate_density_map(self, points: List[Dict], output_path: str) -> str:
        """Generate a matplotlib scatter/density geospatial plot."""
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available for heatmap generation")
            return ""

        valid = [p for p in points if p.get("lat") and p.get("lon")]
        if len(valid) < 2:
            logger.warning("Need at least 2 GPS points for heatmap")
            return ""

        lats = [p["lat"] for p in valid]
        lons = [p["lon"] for p in valid]

        fig, ax = plt.subplots(figsize=(14, 9))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        # Background grid
        ax.grid(True, color="#1c2128", linewidth=0.5, alpha=0.8, zorder=0)

        # Movement path
        ax.plot(lons, lats, "--", color="#00d4ff", alpha=0.3,
                linewidth=1.5, label="Movement Path", zorder=1)

        # Scatter points colored by index
        scatter = ax.scatter(
            lons, lats,
            c=range(len(lats)),
            cmap="plasma",
            s=120,
            alpha=0.9,
            edgecolors="#00d4ff",
            linewidths=0.8,
            zorder=3
        )

        # Number labels
        for i, (lat, lon) in enumerate(zip(lats, lons)):
            ax.annotate(str(i + 1), (lon, lat),
                        textcoords="offset points",
                        xytext=(6, 6),
                        fontsize=7,
                        color="#00d4ff",
                        fontfamily="monospace",
                        alpha=0.8)

        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Evidence Sequence Index", color="#7d8590", fontsize=10)
        cbar.ax.yaxis.set_tick_params(color="#7d8590")
        plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#7d8590")

        ax.set_xlabel("Longitude", color="#7d8590", fontsize=11)
        ax.set_ylabel("Latitude", color="#7d8590", fontsize=11)
        ax.set_title(
            "ForensiX  —  Geospatial Evidence Density Map",
            color="#00d4ff", fontsize=15, fontweight="bold", pad=18,
            fontfamily="monospace"
        )
        ax.tick_params(colors="#7d8590", labelsize=9)
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

        legend = ax.legend(facecolor="#161b22", edgecolor="#30363d",
                           labelcolor="#7d8590", fontsize=9)

        # Stats annotation
        stats_txt = (f"Points: {len(valid)}  |  "
                     f"Lat range: {min(lats):.4f}–{max(lats):.4f}  |  "
                     f"Lon range: {min(lons):.4f}–{max(lons):.4f}")
        fig.text(0.5, 0.01, stats_txt, ha="center", fontsize=8,
                 color="#3d4450", fontfamily="monospace")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        plt.tight_layout(rect=[0, 0.02, 1, 1])
        plt.savefig(output_path, dpi=150, bbox_inches="tight",
                    facecolor="#0d1117", edgecolor="none")
        plt.close()
        logger.info(f"Heatmap saved: {output_path}")
        return output_path

    def generate_frequency_heatmap(self, points: List[Dict], output_path: str) -> str:
        """Generate a 2D frequency/kde heatmap."""
        if not MATPLOTLIB_AVAILABLE:
            return ""
        valid = [p for p in points if p.get("lat") and p.get("lon")]
        if len(valid) < 3:
            return self.generate_density_map(points, output_path)

        lats = np.array([p["lat"] for p in valid])
        lons = np.array([p["lon"] for p in valid])

        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")

        h = ax.hist2d(lons, lats, bins=20,
                      cmap="hot", alpha=0.85)
        plt.colorbar(h[3], ax=ax, label="Visit Frequency")

        ax.scatter(lons, lats, s=30, c="#00d4ff", alpha=0.5,
                   zorder=3, edgecolors="none")

        ax.set_xlabel("Longitude", color="#7d8590")
        ax.set_ylabel("Latitude", color="#7d8590")
        ax.set_title("ForensiX — Location Frequency Heatmap",
                     color="#00d4ff", fontsize=14, fontweight="bold")
        ax.tick_params(colors="#7d8590")
        for spine in ax.spines.values():
            spine.set_edgecolor("#30363d")

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
        plt.close()
        return output_path
