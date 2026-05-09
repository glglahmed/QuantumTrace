"""
Live Map Engine - Folium interactive map generation with real-time updates
"""
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import folium
    from folium.plugins import HeatMap, MarkerCluster
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    logger.warning("folium not installed — map features disabled")

MAP_OUTPUT = os.path.join("temp", "live_map.html")


class LiveMapEngine:

    def generate_map(self, points: List[Dict],
                     show_heatmap: bool = False,
                     show_paths: bool = True) -> str:
        if not FOLIUM_AVAILABLE:
            return self._fallback_map(points)

        os.makedirs("temp", exist_ok=True)

        valid_points = [p for p in points if p.get("lat") and p.get("lon")]

        if not valid_points:
            center = [20.0, 0.0]
            zoom = 2
        else:
            lats = [p["lat"] for p in valid_points]
            lons = [p["lon"] for p in valid_points]
            center = [sum(lats) / len(lats), sum(lons) / len(lons)]
            zoom = 13 if len(valid_points) == 1 else 6

        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="CartoDB dark_matter",
            control_scale=True,
            prefer_canvas=True
        )

        # Add tile layer options
        folium.TileLayer("OpenStreetMap", name="Street Map").add_to(m)
        folium.TileLayer("CartoDB positron", name="Light Map").add_to(m)

        # Marker cluster
        cluster = MarkerCluster(name="Evidence Locations",
                                options={"maxClusterRadius": 40}).add_to(m)

        for i, pt in enumerate(valid_points):
            anomaly_count = pt.get("anomaly_count", 0)
            if anomaly_count > 2:
                color = "red"
                icon_color = "#ff4444"
            elif anomaly_count > 0:
                color = "orange"
                icon_color = "#ff9944"
            else:
                color = "blue"
                icon_color = "#00d4ff"

            popup_html = f"""
            <div style='font-family:monospace;min-width:220px;background:#161b22;
                        color:#c9d1d9;padding:10px;border-radius:4px;'>
              <div style='color:#00d4ff;font-weight:bold;margin-bottom:6px;'>
                📁 {pt.get('filename', 'Unknown')}
              </div>
              <hr style='border-color:#30363d;margin:4px 0'>
              <div>📍 {pt.get('lat',0):.6f}, {pt.get('lon',0):.6f}</div>
              <div>📅 {pt.get('timestamp','N/A')}</div>
              <div>📷 {pt.get('camera','N/A') or 'Unknown camera'}</div>
              <div style='color:{"#f78166" if anomaly_count else "#3fb950"}'>
                ⚠️ Anomalies: {anomaly_count}
              </div>
            </div>
            """

            folium.Marker(
                location=[pt["lat"], pt["lon"]],
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"📁 {pt.get('filename', f'Point {i+1}')}",
                icon=folium.Icon(color=color, icon="camera", prefix="fa")
            ).add_to(cluster)

            # Numbered label
            folium.Marker(
                location=[pt["lat"], pt["lon"]],
                icon=folium.DivIcon(
                    html=f'<div style="font-family:monospace;font-size:9px;'
                         f'color:{icon_color};font-weight:bold;">{i+1}</div>',
                    icon_size=(20, 15),
                    icon_anchor=(10, 0)
                )
            ).add_to(m)

        # Movement path
        if show_paths and len(valid_points) >= 2:
            path_coords = [[p["lat"], p["lon"]] for p in valid_points]
            folium.PolyLine(
                path_coords,
                color="#00d4ff",
                weight=2,
                opacity=0.6,
                dash_array="6 4",
                tooltip="Evidence Movement Path"
            ).add_to(m)

            # Arrows on path
            for i in range(len(path_coords) - 1):
                mid_lat = (path_coords[i][0] + path_coords[i+1][0]) / 2
                mid_lon = (path_coords[i][1] + path_coords[i+1][1]) / 2
                folium.Marker(
                    [mid_lat, mid_lon],
                    icon=folium.DivIcon(
                        html='<div style="color:#00d4ff;font-size:14px;">➤</div>',
                        icon_size=(20, 20),
                        icon_anchor=(10, 10)
                    )
                ).add_to(m)

        # Heatmap overlay
        if show_heatmap and len(valid_points) >= 2:
            heat_data = [[p["lat"], p["lon"]] for p in valid_points]
            HeatMap(
                heat_data,
                name="Evidence Density Heatmap",
                radius=30,
                blur=20,
                max_zoom=13,
                gradient={0.2: "#0000ff", 0.5: "#00ff00",
                           0.7: "#ffff00", 1.0: "#ff0000"}
            ).add_to(m)

        # Summary panel
        summary_html = f"""
        <div style='position:fixed;top:10px;right:10px;z-index:9999;
                    background:#161b22;color:#c9d1d9;padding:12px 16px;
                    border:1px solid #30363d;border-radius:6px;
                    font-family:monospace;font-size:11px;min-width:180px;'>
          <div style='color:#00d4ff;font-weight:bold;font-size:13px;
                      margin-bottom:8px;'>⬡ ForensiX</div>
          <div>📍 GPS Points: <b style='color:#00d4ff'>{len(valid_points)}</b></div>
          <div>📁 Total Evidence: <b style='color:#00d4ff'>{len(points)}</b></div>
          <div style='margin-top:6px;color:#7d8590;font-size:10px;'>
            Live Geospatial Map
          </div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(summary_html))

        folium.LayerControl(collapsed=False).add_to(m)
        m.save(MAP_OUTPUT)
        logger.info(f"Map generated: {len(valid_points)} GPS points plotted")
        return MAP_OUTPUT

    def _fallback_map(self, points: List[Dict]) -> str:
        os.makedirs("temp", exist_ok=True)
        rows = ""
        for p in points[:20]:
            rows += (f"<tr><td>{p.get('filename','')}</td>"
                     f"<td>{p.get('lat','')}</td><td>{p.get('lon','')}</td></tr>")
        html = f"""<!DOCTYPE html>
<html><body style='background:#0d1117;color:#c9d1d9;font-family:monospace;padding:40px;'>
<h2 style='color:#00d4ff'>ForensiX — Map (folium not installed)</h2>
<p style='color:#7d8590'>Install folium: <code>pip install folium</code></p>
<p>GPS Points found: {len(points)}</p>
<table border='1' style='border-color:#30363d;width:100%;'>
<tr style='color:#00d4ff'><th>Filename</th><th>Lat</th><th>Lon</th></tr>
{rows}
</table></body></html>"""
        with open(MAP_OUTPUT, "w") as f:
            f.write(html)
        return MAP_OUTPUT
