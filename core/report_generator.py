"""
ForensiX — Professional Forensic Report Generator
Full metadata, per-image EXIF tables, thumbnails, GPS, validation, chain of custody.
"""

import os
import io
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        HRFlowable, PageBreak, KeepTogether, Image as RLImage,
    )
    from reportlab.pdfgen import canvas as pdfgen_canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image as PILImage
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# ── Colours ────────────────────────────────────────────────────────────────
C_DARK   = "#0d1117"; C_DARK2 = "#161b22"; C_DARK3 = "#1c2128"; C_DARK4 = "#21262d"
C_BORDER = "#30363d"; C_BLUE  = "#58a6ff"; C_CYAN  = "#00d4ff"; C_GREEN = "#3fb950"
C_ORANGE = "#d29922"; C_RED   = "#f85149"; C_GRAY  = "#8b949e"; C_WHITE = "#e6edf3"
C_YELLOW = "#e3b341"; VERSION = "ForensiX DFIR v2.0"

_STYLES: Dict = {}

# ══════════════════════════════════════════════════════════════════════════════

class _NumberedCanvas(pdfgen_canvas.Canvas):
    def __init__(self, *args, case_name="ForensiX", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []; self._case = case_name
    def showPage(self):
        self._saved.append(dict(self.__dict__)); self._startPage()
    def save(self):
        n = len(self._saved)
        for s in self._saved:
            self.__dict__.update(s); self._chrome(n)
            pdfgen_canvas.Canvas.showPage(self)
        pdfgen_canvas.Canvas.save(self)
    def _chrome(self, total):
        self.saveState(); W, H = A4
        self.setFillColor(colors.HexColor(C_DARK2))
        self.rect(0, H-1.1*cm, W, 1.1*cm, fill=1, stroke=0)
        self.setFillColor(colors.HexColor(C_CYAN))
        self.rect(0, H-1.1*cm, W, 2, fill=1, stroke=0)
        self.setFont("Courier-Bold", 8); self.setFillColor(colors.HexColor(C_CYAN))
        self.drawString(1.5*cm, H-0.75*cm, VERSION)
        self.setFont("Courier", 7); self.setFillColor(colors.HexColor(C_GRAY))
        self.drawRightString(W-1.5*cm, H-0.75*cm, f"CASE: {self._case}  |  CONFIDENTIAL")
        self.setFillColor(colors.HexColor(C_DARK2))
        self.rect(0, 0, W, 1.0*cm, fill=1, stroke=0)
        self.setFillColor(colors.HexColor(C_BORDER))
        self.rect(0, 1.0*cm, W, 0.5, fill=1, stroke=0)
        self.setFont("Courier", 7); self.setFillColor(colors.HexColor(C_GRAY))
        self.drawString(1.5*cm, 0.35*cm, datetime.now().strftime("Generated: %Y-%m-%d %H:%M:%S UTC"))
        self.setFillColor(colors.HexColor(C_BLUE))
        self.drawRightString(W-1.5*cm, 0.35*cm, f"Page {self._pageNumber} of {total}")
        self.restoreState()

# ══════════════════════════════════════════════════════════════════════════════

def _init():
    global _STYLES
    if _STYLES: return
    def P(n, **kw):
        d = dict(fontName="Courier", fontSize=9, textColor=colors.HexColor(C_WHITE))
        d.update(kw); return ParagraphStyle(n, **d)
    _STYLES = {
        "title":  P("T",  fontSize=30, textColor=colors.HexColor(C_CYAN), alignment=TA_CENTER, fontName="Courier-Bold", spaceAfter=4, leading=34),
        "sub":    P("S",  fontSize=10, textColor=colors.HexColor(C_GRAY),  alignment=TA_CENTER, spaceAfter=3),
        "h1":     P("H1", fontSize=15, textColor=colors.HexColor(C_CYAN),  fontName="Courier-Bold", spaceBefore=14, spaceAfter=6),
        "h2":     P("H2", fontSize=11, textColor=colors.HexColor(C_BLUE),  fontName="Courier-Bold", spaceBefore=10, spaceAfter=4),
        "h3":     P("H3", fontSize=9,  textColor=colors.HexColor(C_YELLOW),fontName="Courier-Bold", spaceBefore=6,  spaceAfter=3),
        "body":   P("B",  fontSize=8,  textColor=colors.HexColor(C_GRAY),  spaceAfter=3, leading=12),
        "mono":   P("M",  fontSize=7.5,textColor=colors.HexColor(C_WHITE), spaceAfter=2, leading=11),
        "label":  P("L",  fontSize=7.5,textColor=colors.HexColor(C_GRAY),  spaceAfter=1),
        "value":  P("V",  fontSize=7.5,textColor=colors.HexColor(C_WHITE), spaceAfter=1),
    }

def _hr(c=C_BORDER, t=0.5):
    return HRFlowable(width="100%", color=colors.HexColor(c), thickness=t, spaceAfter=4, spaceBefore=4)

def _tbl(data, widths, hbg=C_BLUE, hfg=C_DARK, alt1=C_DARK2, alt2=C_DARK3, small=False):
    fs = 7 if small else 8
    ts = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  colors.HexColor(hbg)),
        ("TEXTCOLOR",     (0,0),(-1,0),  colors.HexColor(hfg)),
        ("FONTNAME",      (0,0),(-1,0),  "Courier-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), fs),
        ("FONTNAME",      (0,1),(-1,-1), "Courier"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.HexColor(alt1), colors.HexColor(alt2)]),
        ("TEXTCOLOR",     (0,1),(-1,-1), colors.HexColor(C_WHITE)),
        ("GRID",          (0,0),(-1,-1), 0.3, colors.HexColor(C_BORDER)),
        ("TOPPADDING",    (0,0),(-1,-1), 4), ("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",   (0,0),(-1,-1), 6), ("RIGHTPADDING", (0,0),(-1,-1),6),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ])
    t = Table(data, colWidths=widths, repeatRows=1); t.setStyle(ts); return t, ts

def _kv(pairs, c1=6*cm, c2=None):
    W = A4[0]-4*cm; c2 = c2 or W-c1
    rows = [[Paragraph(str(k), _STYLES["label"]), Paragraph(str(v) if v is not None else "—", _STYLES["value"])] for k,v in pairs]
    if not rows: return None
    ts = TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), colors.HexColor(C_DARK3)),
        ("BACKGROUND",    (1,0),(1,-1), colors.HexColor(C_DARK2)),
        ("GRID",          (0,0),(-1,-1),0.25, colors.HexColor(C_BORDER)),
        ("TOPPADDING",    (0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",   (0,0),(-1,-1),6), ("RIGHTPADDING", (0,0),(-1,-1),6),
        ("VALIGN",        (0,0),(-1,-1),"TOP"),
    ])
    t = Table(rows, colWidths=[c1,c2]); t.setStyle(ts); return t

def _thumb(fp, px=110):
    if not PILLOW_AVAILABLE or not fp or not os.path.exists(fp): return None
    try:
        img = PILImage.open(fp).convert("RGB"); img.thumbnail((px,px), PILImage.LANCZOS)
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=70); buf.seek(0)
        w,h = img.size
        return RLImage(buf, width=w*0.75, height=h*0.75)
    except Exception: return None

# ══════════════════════════════════════════════════════════════════════════════

def _cover(case, stats, op):
    _init(); S = _STYLES; W = A4[0]-4*cm; out = []
    out += [Spacer(1,1.5*cm), Paragraph("ForensiX", S["title"]),
            Paragraph("Digital Forensics Investigation Report", S["sub"]),
            Spacer(1,0.3*cm), _hr(C_CYAN,2), Spacer(1,0.4*cm)]
    info = [["Case Name", case], ["Report Date", datetime.now().strftime("%A, %d %B %Y — %H:%M:%S UTC")],
            ["Platform", VERSION], ["Operator", op], ["Classification","CONFIDENTIAL — Chain of Custody Protected"]]
    ti = Table([[Paragraph(k,S["label"]),Paragraph(v,S["value"])] for k,v in info], colWidths=[5*cm,W-5*cm])
    ti.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor(C_DARK3)),("BACKGROUND",(1,0),(1,-1),colors.HexColor(C_DARK2)),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor(C_BORDER)),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),("FONTNAME",(0,0),(0,-1),"Courier-Bold")]))
    out.append(ti); out.append(Spacer(1,0.8*cm))
    tot=stats.get("total_images",0); gps=stats.get("with_gps",0)
    anom=stats.get("total_anomalies",0); crit=stats.get("critical_anomalies",0)
    def cell(lbl,val,fg):
        return [Paragraph(f'<font color="{fg}"><b>{val}</b></font>',
            ParagraphStyle("sv",fontName="Courier-Bold",fontSize=22,textColor=colors.HexColor(fg),alignment=TA_CENTER)),
                Paragraph(lbl,ParagraphStyle("sl",fontName="Courier",fontSize=8,textColor=colors.HexColor(C_GRAY),alignment=TA_CENTER))]
    cells = [cell("Total Images",tot,C_CYAN), cell("With GPS",gps,C_GREEN),
             cell("Anomalies",anom,C_ORANGE), cell("Critical",crit,C_RED)]
    sd = [[c[0] for c in cells],[c[1] for c in cells]]
    st2=Table(sd,colWidths=[W/4]*4)
    st2.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(C_DARK3)),
        ("GRID",(0,0),(-1,-1),1,colors.HexColor(C_BORDER)),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),10)]))
    out += [st2, PageBreak()]; return out

def _toc():
    _init(); S = _STYLES; out = [Paragraph("Table of Contents",S["h1"]), _hr(C_CYAN,1.5)]
    rows = [["§","Section"],["1","Executive Summary"],["2","Evidence Inventory"],
            ["3","Per-Image Full Details"],["4","GPS & Location Summary"],
            ["5","Anomaly Detection Report"],["6","Validation Results"],
            ["7","Chain of Custody Log"],["8","Chain of Custody Declaration"]]
    t,_ = _tbl(rows,[1.5*cm,15.5*cm]); out += [t, PageBreak()]; return out

def _exec_summary(stats, evlist, anoms):
    _init(); S = _STYLES; W = A4[0]-4*cm; out = [Paragraph("1. Executive Summary",S["h1"]), _hr(C_CYAN,1.5)]
    tot=stats.get("total_images",0); gps=stats.get("with_gps",0)
    anom=stats.get("total_anomalies",0); crit=stats.get("critical_anomalies",0)
    high=stats.get("high_anomalies",0)
    out.append(Paragraph("Key Metrics",S["h2"]))
    md=[["Metric","Value","Notes"],
        ["Total Images Analysed",str(tot),"All ingested evidence items"],
        ["Images with GPS Data",str(gps),f"{gps/max(tot,1)*100:.1f}% of total"],
        ["Images without GPS",str(tot-gps),f"{(tot-gps)/max(tot,1)*100:.1f}% of total"],
        ["Total Anomalies",str(anom),"All severity levels"],
        ["Critical",str(crit),"Immediate attention required"],
        ["High",str(high),"Review recommended"],
        ["Medium / Low",str(max(anom-crit-high,0)),"Informational"]]
    t,ts=_tbl(md,[7*cm,3*cm,7*cm])
    for i,r in enumerate(md[1:],1):
        if "Critical" in r[0]: ts.add("TEXTCOLOR",(0,i),(-1,i),colors.HexColor(C_RED))
        elif "High" in r[0]: ts.add("TEXTCOLOR",(0,i),(-1,i),colors.HexColor(C_ORANGE))
    t.setStyle(ts); out += [t, Spacer(1,0.4*cm)]
    # camera breakdown
    makes={}
    for ev in evlist:
        mk=(ev.get("camera_make") or "Unknown").strip() or "Unknown"; makes[mk]=makes.get(mk,0)+1
    if makes:
        out.append(Paragraph("Camera / Device Breakdown",S["h2"]))
        cd=[["Make","Count","Share"]]+[[mk,str(c),f"{c/max(tot,1)*100:.1f}%"] for mk,c in sorted(makes.items(),key=lambda x:-x[1])]
        t2,_=_tbl(cd,[8*cm,3*cm,6*cm]); out += [t2, Spacer(1,0.4*cm)]
    # anomaly severity
    if anoms:
        out.append(Paragraph("Anomaly Severity Breakdown",S["h2"]))
        sc={}
        for a in anoms: sc[a.get("severity","?")] = sc.get(a.get("severity","?"),0)+1
        ad=[["Severity","Count","% of Anomalies"]]
        for sev,fg in [("CRITICAL",C_RED),("HIGH",C_ORANGE),("MEDIUM",C_YELLOW),("LOW",C_GREEN)]:
            c=sc.get(sev,0)
            if c: ad.append([sev,str(c),f"{c/max(anom,1)*100:.1f}%"])
        t3,ts3=_tbl(ad,[6*cm,3*cm,8*cm])
        for i2,r2 in enumerate(ad[1:],1):
            fg_map={"CRITICAL":C_RED,"HIGH":C_ORANGE,"MEDIUM":C_YELLOW,"LOW":C_GREEN}
            if r2[0] in fg_map: ts3.add("TEXTCOLOR",(0,i2),(0,i2),colors.HexColor(fg_map[r2[0]]))
        t3.setStyle(ts3); out.append(t3)
    out.append(PageBreak()); return out

def _inventory(evlist):
    _init(); S = _STYLES; out = [Paragraph("2. Evidence Inventory",S["h1"]), _hr(C_CYAN,1.5)]
    if not evlist:
        out += [Paragraph("No evidence items.",S["body"]), PageBreak()]; return out
    hdr=[["#","Filename","Format","Size KB","GPS","Camera","SHA-256"]]
    rows=[]
    for i,ev in enumerate(evlist,1):
        sha=(ev.get("sha256") or ""); sha_s=sha[:8]+"…"+sha[-8:] if len(sha)>=16 else sha or "N/A"
        rows.append([str(i),(ev.get("filename") or "")[:30],(ev.get("format") or "").lstrip(".").upper(),
            f"{(ev.get('filesize') or 0)/1024:.1f}","✓" if ev.get("has_gps") else "✗",
            f"{ev.get('camera_make','')} {ev.get('camera_model','')}".strip()[:24] or "Unknown",sha_s])
    t,ts=_tbl(hdr+rows,[0.7*cm,4.5*cm,1.5*cm,1.8*cm,1.2*cm,4*cm,3.3*cm],small=True)
    for i,ev in enumerate(evlist,1):
        c=C_GREEN if ev.get("has_gps") else C_RED; ts.add("TEXTCOLOR",(4,i),(4,i),colors.HexColor(c))
    t.setStyle(ts); out += [t, PageBreak()]; return out

def _per_image(evlist):
    _init(); S = _STYLES; W = A4[0]-4*cm
    out = [Paragraph("3. Per-Image Full Details",S["h1"]), _hr(C_CYAN,1.5),
           Paragraph("Complete extracted metadata for each evidence image.",S["body"]),
           Spacer(1,0.3*cm)]
    for idx,ev in enumerate(evlist,1):
        fn = ev.get("filename") or f"image_{idx}"; fp = ev.get("filepath","")
        meta = {}
        try: meta = json.loads(ev.get("metadata_json") or "{}")
        except Exception: pass
        blk = []
        blk.append(Paragraph(f'<b>{idx:03d} — {fn}</b>',
            ParagraphStyle("ch",fontName="Courier-Bold",fontSize=10,textColor=colors.HexColor(C_CYAN),
                           backColor=colors.HexColor(C_DARK2),borderPad=5)))
        blk.append(Spacer(1,0.15*cm))
        # thumb + basic
        thumb = _thumb(fp)
        sha=(ev.get("sha256") or ""); md5=(ev.get("md5") or "")
        basic=[("Filepath",fp or "—"),("Format",(ev.get("format") or "").lstrip(".").upper() or "—"),
               ("File Size",f"{(ev.get('filesize') or 0)/1024:.2f} KB"),
               ("SHA-256",sha or "—"),("MD5",md5 or "—"),("Ingested At",ev.get("added_at") or "—")]
        bt = _kv(basic, c1=3*cm, c2=9.5*cm)
        if thumb and bt:
            side=Table([[thumb,bt]],colWidths=[2.8*cm,W-2.8*cm])
            side.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0)]))
            blk.append(side)
        elif bt: blk.append(bt)
        blk.append(Spacer(1,0.2*cm))
        # camera
        blk.append(Paragraph("Camera & Device",S["h3"]))
        cam=[("Make",ev.get("camera_make") or "—"),("Model",ev.get("camera_model") or "—"),
             ("Software",ev.get("software") or meta.get("software") or "—")]
        ct=_kv(cam); blk.append(ct) if ct else None
        blk.append(Spacer(1,0.15*cm))
        # timestamps
        ts_dict = meta.get("timestamps",{})
        ts_orig = ev.get("timestamp_original") or ""
        if ts_dict or ts_orig:
            blk.append(Paragraph("Timestamps",S["h3"]))
            tp=[]; 
            if ts_orig: tp.append(("DateTimeOriginal",ts_orig))
            for k,v in ts_dict.items():
                if k != "DateTimeOriginal": tp.append((k,v))
            tt=_kv(tp);
            if tt: blk.append(tt)
            blk.append(Spacer(1,0.15*cm))
        # GPS
        blk.append(Paragraph("GPS & Location",S["h3"]))
        lat=ev.get("lat"); lon=ev.get("lon")
        if ev.get("has_gps") and lat is not None:
            gps_meta=meta.get("gps",{}); coords=gps_meta.get("coordinates") or {}
            alt=coords.get("altitude") if isinstance(coords,dict) else None
            raw_gps=gps_meta.get("raw",{})
            gp=[("Latitude",f"{lat:.7f}°"),("Longitude",f"{lon:.7f}°"),
                ("Altitude",f"{alt:.1f} m" if alt is not None else "—"),
                ("Maps Link",f"https://maps.google.com/?q={lat:.6f},{lon:.6f}")]
            for k,v in raw_gps.items():
                if k not in ("GPSLatitude","GPSLongitude","GPSAltitude"): gp.append((f"GPS {k}",str(v)))
            gt=_kv(gp);
            if gt: blk.append(gt)
        else:
            blk.append(Paragraph("No GPS data present in this image.",S["body"]))
        blk.append(Spacer(1,0.15*cm))
        # image info
        ii=meta.get("image_info",{})
        if ii:
            blk.append(Paragraph("Image Properties",S["h3"]))
            iw=ii.get("width",0); ih=ii.get("height",0)
            ip=[("Dimensions",f"{iw} × {ih} px"),("Megapixels",f"{iw*ih/1e6:.2f} MP" if iw and ih else "—"),
                ("Color Mode",ii.get("mode","—")),("Image Format",ii.get("format","—"))]
            it=_kv(ip);
            if it: blk.append(it)
            blk.append(Spacer(1,0.15*cm))
        # full raw exif
        raw=meta.get("raw_exif",{})
        if raw:
            blk.append(Paragraph("Full EXIF Metadata",S["h3"]))
            ed=[["Tag","Value"]]+[[str(k)[:40],str(v)[:80]] for k,v in sorted(raw.items())]
            et,_=_tbl(ed,[6*cm,11*cm],small=True); blk.append(et)
            blk.append(Spacer(1,0.15*cm))
        # errors
        errs=meta.get("errors",[])
        if errs:
            blk.append(Paragraph("Extraction Warnings",S["h3"]))
            for e in errs:
                blk.append(Paragraph(f"⚠ {e}",ParagraphStyle("ew",fontName="Courier",fontSize=7.5,textColor=colors.HexColor(C_ORANGE))))
        blk.append(_hr(C_BORDER,0.5))
        out.append(KeepTogether(blk[:5]))
        for item in blk[5:]: out.append(item)
    out.append(PageBreak()); return out

def _gps_summary(evlist):
    _init(); S = _STYLES
    out = [Paragraph("4. GPS & Location Summary",S["h1"]), _hr(C_CYAN,1.5)]
    gps=[ev for ev in evlist if ev.get("has_gps") and ev.get("lat") is not None]
    if not gps:
        out += [Paragraph("No GPS-tagged images found.",S["body"]), PageBreak()]; return out
    out.append(Paragraph(f"{len(gps)} of {len(evlist)} images contain GPS data.",S["body"]))
    out.append(Spacer(1,0.3*cm))
    hdr=[["#","Filename","Latitude","Longitude","Captured","Camera"]]
    rows=[]
    for i,ev in enumerate(gps,1):
        ts=(ev.get("timestamp_original") or "—")[:19]
        cam=f"{ev.get('camera_make','')} {ev.get('camera_model','')}".strip()
        rows.append([str(i),(ev.get("filename") or "")[:28],f"{ev['lat']:.6f}°",f"{ev['lon']:.6f}°",ts,cam[:20] or "Unknown"])
    t,_=_tbl(hdr+rows,[0.7*cm,4.3*cm,2.8*cm,2.8*cm,3.5*cm,3*cm],small=True)
    out += [t, PageBreak()]; return out

def _anomalies(anoms):
    _init(); S = _STYLES
    out = [Paragraph("5. Anomaly Detection Report",S["h1"]), _hr(C_CYAN,1.5)]
    if not anoms:
        out += [Paragraph("No anomalies detected.",S["body"]), PageBreak()]; return out
    sev_cfg=[("CRITICAL",C_RED,C_WHITE),("HIGH",C_ORANGE,C_DARK),("MEDIUM",C_YELLOW,C_DARK),("LOW",C_GREEN,C_DARK)]
    for sev,hbg,hfg in sev_cfg:
        grp=[a for a in anoms if (a.get("severity") or "").upper()==sev]
        if not grp: continue
        out.append(Paragraph(f'{sev} — {len(grp)} anomal{"y" if len(grp)==1 else "ies"}',S["h2"]))
        hdr=[["Type","Field","Detail","Ev.ID"]]
        rows=[[( a.get("anomaly_type") or a.get("type") or "Unknown")[:35],
               (a.get("field") or "—")[:20],(a.get("detail") or "—")[:70],
               str(a.get("evidence_id") or "—")] for a in grp]
        t,_=_tbl(hdr+rows,[4*cm,2.5*cm,9*cm,1.5*cm],hbg=hbg,hfg=hfg,small=True)
        out += [t, Spacer(1,0.4*cm)]
    out.append(PageBreak()); return out

def _validation(evlist):
    _init(); S = _STYLES
    out = [Paragraph("6. Validation Results",S["h1"]), _hr(C_CYAN,1.5)]
    SC = {"PASS":C_GREEN,"WARN":C_ORANGE,"FAIL":C_RED}
    for ev in evlist:
        meta={}
        try: meta=json.loads(ev.get("metadata_json") or "{}")
        except Exception: pass
        fn=ev.get("filename") or "—"; sha=ev.get("sha256") or ""; ts=ev.get("timestamp_original") or ""
        lat=ev.get("lat"); lon=ev.get("lon"); ii=meta.get("image_info",{}); w=ii.get("width",0); h=ii.get("height",0)
        checks=[
            ("File Integrity",   "PASS" if sha else "FAIL", f"SHA-256: {sha[:16]}…" if sha else "No hash"),
            ("EXIF Completeness","PASS" if meta.get("raw_exif") else "WARN", f"{len(meta.get('raw_exif',{}))} EXIF tags"),
            ("Camera Metadata",  "PASS" if ev.get("camera_make") else "WARN", f"{ev.get('camera_make','')} {ev.get('camera_model','')}".strip() or "Missing"),
            ("Timestamp",        "PASS" if ts else "WARN", ts or "No DateTimeOriginal"),
            ("GPS Validity",     "PASS" if (lat is not None and -90<=lat<=90 and -180<=lon<=180) else "WARN",
             f"({lat:.4f}, {lon:.4f})" if lat is not None else "No GPS data"),
            ("Image Dimensions", "PASS" if (w>0 and h>0) else "WARN", f"{w}×{h}" if w and h else "Unknown"),
        ]
        p=sum(1 for _,s,_ in checks if s=="PASS"); w2=sum(1 for _,s,_ in checks if s=="WARN"); f=sum(1 for _,s,_ in checks if s=="FAIL")
        ov="FAIL" if f else ("WARN" if w2 else "PASS"); ovc=SC.get(ov,C_GRAY)
        out.append(Paragraph(f'<b>{fn}</b>  <font color="{ovc}">[{ov}]</font>  ✓{p}  ⚠{w2}  ✗{f}',
            ParagraphStyle("vh",fontName="Courier-Bold",fontSize=9,textColor=colors.HexColor(C_WHITE))))
        hdr=[["Check","Status","Detail"]]
        rows=[[cn,st,dt] for cn,st,dt in checks]
        t,ts2=_tbl(hdr+rows,[5*cm,2*cm,10*cm],small=True)
        for i,(cn,st,dt) in enumerate(checks,1):
            sc=SC.get(st,C_GRAY); ts2.add("TEXTCOLOR",(1,i),(1,i),colors.HexColor(sc)); ts2.add("FONTNAME",(1,i),(1,i),"Courier-Bold")
        t.setStyle(ts2); out += [t, Spacer(1,0.4*cm)]
    out.append(PageBreak()); return out

def _custody(evlist):
    _init(); S = _STYLES
    out = [Paragraph("7. Chain of Custody Log",S["h1"]), _hr(C_CYAN,1.5),
           Paragraph("Every forensic action performed on each evidence item. All operations read-only.",S["body"]),
           Spacer(1,0.3*cm)]
    hdr=[["Timestamp","Evidence ID","Filename","Action","Operator"]]
    rows=[]
    for ev in evlist:
        ts=(ev.get("added_at") or "—")[:19]; eid=str(ev.get("id") or "—")
        fn=(ev.get("filename") or "—")[:30]; sha=(ev.get("sha256") or "")[:16]
        rows.append([ts,eid,fn,f"INGESTED | SHA256:{sha}…","ForensiX Auto"])
    t,_=_tbl(hdr+rows,[3.8*cm,1.5*cm,4*cm,5.5*cm,2.2*cm],small=True)
    out += [t, PageBreak()]; return out

def _declaration():
    _init(); S = _STYLES
    out = [Paragraph("8. Chain of Custody Declaration",S["h1"]), _hr(C_CYAN,1.5)]
    paras=[
        ("Evidence Handling","All evidence files were processed in strict read-only mode. No original file was modified, moved, or deleted during the investigation."),
        ("Hash Verification","SHA-256 and MD5 cryptographic hashes were computed at ingestion and stored immutably. These hashes serve as a tamper-evident seal for each evidence item."),
        ("Metadata Extraction","EXIF metadata was extracted using industry-standard libraries. GPS coordinates, camera information, timestamps, and all available tags were recorded verbatim."),
        ("Anomaly Detection","Anomalies were identified through automated heuristic analysis. All flagged items should be reviewed by a qualified forensic examiner before drawing conclusions."),
        ("Report Integrity",f"This report was generated automatically by {VERSION}. It represents a point-in-time snapshot of the case database."),
        ("Disclaimer","This report is intended solely for the named case and authorised personnel. Unauthorised disclosure, reproduction, or distribution is prohibited."),
    ]
    for title,text in paras:
        out += [Paragraph(title,S["h2"]), Paragraph(text,S["body"]), Spacer(1,0.2*cm)]
    out.append(Spacer(1,0.8*cm)); out.append(_hr(C_BORDER))
    sig=Table([["Examiner Name:","________________________________","Date:",datetime.now().strftime("%Y-%m-%d")],
               ["Digital Signature:","________________________________","Case Ref:","________________________________"]],
              colWidths=[4*cm,6*cm,2.5*cm,4.5*cm])
    sig.setStyle(TableStyle([("FONTNAME",(0,0),(-1,-1),"Courier"),("FONTSIZE",(0,0),(-1,-1),8),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor(C_GRAY)),("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),0)]))
    out.append(sig); return out

# ══════════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    def generate(self, evidence_list, anomalies, stats, output_path,
                 case_name="ForensiX Case", operator="Forensic Examiner"):
        if not REPORTLAB_AVAILABLE:
            return self._text_report(evidence_list, anomalies, stats, output_path, case_name)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        _init()
        doc = SimpleDocTemplate(output_path, pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm, topMargin=1.6*cm, bottomMargin=1.4*cm,
            title=f"ForensiX Report — {case_name}", author=VERSION,
            subject="Digital Forensics Investigation Report", creator=VERSION)
        story = []
        story += _cover(case_name, stats, operator)
        story += _toc()
        story += _exec_summary(stats, evidence_list, anomalies)
        story += _inventory(evidence_list)
        story += _per_image(evidence_list)
        story += _gps_summary(evidence_list)
        story += _anomalies(anomalies)
        story += _validation(evidence_list)
        story += _custody(evidence_list)
        story += _declaration()
        def mk(*a, **kw): return _NumberedCanvas(*a, case_name=case_name, **kw)
        doc.build(story, canvasmaker=mk)
        logger.info(f"Professional PDF report: {output_path}")
        return output_path

    def _text_report(self, evlist, anoms, stats, output_path, case_name):
        sep="="*80
        lines=[sep, "  FORENSIX — DIGITAL FORENSICS INVESTIGATION REPORT",
               f"  Case: {case_name}", f"  Generated: {datetime.now().isoformat()}",
               f"  Platform: {VERSION}", sep, "", "EXECUTIVE SUMMARY", "-"*40]
        for k,v in stats.items(): lines.append(f"  {k:<35} {v}")
        lines += ["", "EVIDENCE INVENTORY", "-"*40]
        for i,ev in enumerate(evlist,1):
            lines.append(f"  {i:03d}  {ev.get('filename',''):<35}  GPS:{'Y' if ev.get('has_gps') else 'N'}  {(ev.get('sha256') or '')[:16]}…")
        lines += ["", "ANOMALIES", "-"*40]
        for a in anoms:
            lines.append(f"  [{a.get('severity','?'):8}] {(a.get('anomaly_type') or a.get('type','Unknown')):<35}  {a.get('detail','')}")
        lines += ["", sep, "  ForensiX DFIR  |  Chain of Custody Protected", sep]
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        txt=output_path.replace(".pdf",".txt")
        with open(txt,"w",encoding="utf-8") as f: f.write("\n".join(lines))
        return txt