#!/usr/bin/env python3
"""
Handwriting Forensics Studio — GUI front-end.
Tabs: Analysis | Handwriting | Forgery | OCR | Metadata | Report
"""
from __future__ import annotations
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageTk

sys.path.insert(0, os.path.dirname(__file__))
from modules.ela import ela_sweep, overlay_suspicious, ela_verdict
from modules.forgery import (copy_move_detection, overlay_copy_move,
                             noise_fingerprint, pixel_statistics)
from modules.handwriting import HandwritingMetrics
from modules.metadata import full_metadata
from modules.ocr_engine import OcrEngine, LANGUAGES
from modules import report as report_mod

TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".exhibits")
os.makedirs(TMP, exist_ok=True)


class ImageViewer(tk.Frame):
    """Scrollable, zoomable canvas viewer (wheel = zoom, drag = pan)."""
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.canvas = tk.Canvas(self, bg="#222", highlightthickness=0)
        vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(self, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        vbar.pack(side="right", fill="y"); hbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.photo = None
        self._img = None
        self.zoom = 1.0
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag)

    def show_pil(self, pil_img: Image.Image):
        self._img = pil_img.convert("RGB")
        self.zoom = 1.0
        self._render()

    def _render(self):
        if self._img is None:
            return
        w = max(int(self._img.width * self.zoom), 1)
        h = max(int(self._img.height * self.zoom), 1)
        resized = self._img.resize((w, h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, w, h))

    def _zoom(self, e):
        self.zoom *= 1.15 if e.delta > 0 else 0.87
        self.zoom = min(max(self.zoom, 0.05), 20.0)
        self._render()

    def _drag_start(self, e):
        self.canvas.scan_mark(e.x, e.y)

    def _drag(self, e):
        self.canvas.scan_dragto(e.x, e.y, gain=1)


class ForensicsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Handwriting Forensics Studio")
        self.geometry("1440x860")
        self.configure(bg="#0f0f1a")
        self.path = None
        self.original_bgr = None
        self.ocr_engine = OcrEngine()
        self.results = {}

        self._build_menu()
        self._build_ui()
        self.status("Ready — File ▸ Open Image to begin.")

    # ------------------------------------------------------------- UI build
    def _build_menu(self):
        m = tk.Menu(self)
        fm = tk.Menu(m, tearoff=0)
        fm.add_command(label="Open Image…", accelerator="Ctrl+O",
                       command=self.open_image)
        fm.add_command(label="Export PDF Report…", command=self.export_pdf)
        fm.add_command(label="Export HTML Report…", command=self.export_html)
        fm.add_separator()
        fm.add_command(label="Exit", command=self.destroy)
        m.add_cascade(label="File", menu=fm)
        hm = tk.Menu(m, tearoff=0)
        hm.add_command(label="About", command=self._about)
        m.add_cascade(label="Help", menu=hm)
        self.config(menu=m)
        self.bind("<Control-o>", lambda e: self.open_image())

    def _build_ui(self):
        # top control bar
        bar = tk.Frame(self, bg="#16213e", padx=8, pady=6)
        bar.pack(side="top", fill="x")
        tk.Label(bar, text="ELA quality:", bg="#16213e", fg="#eee",
                 font=("Segoe UI", 10)).pack(side="left")
        self.ela_q = tk.IntVar(value=90)
        ttk.Spinbox(bar, from_=50, to=98, textvariable=self.ela_q,
                    width=5).pack(side="left", padx=4)
        ttk.Button(bar, text="Run Full Analysis",
                   command=self.run_all).pack(side="left", padx=12)

        # language picker (multi-select via listbox)
        tk.Label(bar, text="OCR languages:", bg="#16213e", fg="#eee",
                 font=("Segoe UI", 10)).pack(side="left", padx=(20, 4))
        self.lang_var = tk.StringVar(value="eng")
        self.lang_combo = ttk.Combobox(
            bar, textvariable=self.lang_var, width=24,
            values=[f"{k} — {v}" for k, v in LANGUAGES.items()])
        self.lang_combo.pack(side="left")
        tk.Label(bar, text="(comma-sep: eng,hin,urd)",
                 bg="#16213e", fg="#9aa").pack(side="left", padx=4)
        ttk.Button(bar, text="Run OCR", command=self.run_ocr).pack(
            side="left", padx=8)

        # main area: viewer + notebook
        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=6, pady=6)

        left = tk.Frame(main, bg="#111")
        tk.Label(left, text="ORIGINAL (wheel=zoom, drag=pan)",
                 bg="#111", fg="#9aa", font=("Segoe UI", 9)).pack(anchor="w")
        self.view_orig = ImageViewer(left, height=480)
        self.view_orig.pack(fill="both", expand=True)
        main.add(left, weight=1)

        right = tk.Frame(main, bg="#111")
        tk.Label(right, text="ANALYSIS OUTPUT",
                 bg="#111", fg="#9aa", font=("Segoe UI", 9)).pack(anchor="w")
        self.view_res = ImageViewer(right, height=480)
        self.view_res.pack(fill="both", expand=True)
        main.add(right, weight=1)

        # notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=False, padx=6, pady=(0, 6))
        self.txt_handwriting = self._make_text_tab("Handwriting Profile")
        self.txt_forgery = self._make_text_tab("Forgery & ELA")
        self.txt_ocr = self._make_text_tab("Extracted Text")
        self.txt_metadata = self._make_text_tab("File Metadata")
        self.txt_concl = self._make_text_tab("Conclusions")
        self._tab_handwriting = self.nb.tabs()[0]
        self._tab_forgery = self.nb.tabs()[1]
        self._tab_ocr = self.nb.tabs()[2]
        self._tab_meta = self.nb.tabs()[3]
        self._tab_concl = self.nb.tabs()[4]

        # status bar
        self.status_var = tk.StringVar()
        tk.Label(self, textvariable=self.status_var, anchor="w",
                 bg="#16213e", fg="#ccc", padx=10).pack(side="bottom", fill="x")

    def _make_text_tab(self, title) -> tk.Text:
        frame = tk.Frame(self.nb)
        self.nb.add(frame, text=title)
        txt = tk.Text(frame, bg="#0d0d18", fg="#e8e8f0", insertbackground="white",
                      wrap="word", font=("Consolas", 10), height=12)
        sb = ttk.Scrollbar(frame, command=txt.yview)
        txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); txt.pack(fill="both", expand=True)
        return txt

    def status(self, msg: str):
        self.status_var.set(f"  {msg}")

    # ------------------------------------------------------------- actions
    def open_image(self):
        p = filedialog.askopenfilename(
            title="Select questioned document image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"),
                       ("All files", "*.*")])
        if not p:
            return
        self.path = p
        self.original_bgr = cv2.imread(p)
        if self.original_bgr is None:
            messagebox.showerror("Error", "Could not decode image.")
            return
        rgb = cv2.cvtColor(self.original_bgr, cv2.COLOR_BGR2RGB)
        self.view_orig.show_pil(Image.fromarray(rgb))
        self.view_res.show_pil(Image.fromarray(rgb))
        self.status(f"Loaded: {os.path.basename(p)}")

    def run_all(self):
        if self.original_bgr is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        self.status("Running full analysis…")
        threading.Thread(target=self._run_all_worker, daemon=True).start()

    def _run_all_worker(self):
        try:
            self.run_ela(show=False)
            self.run_handwriting(show=False)
            self.run_forgery(show=False)
            self.run_ocr()
            self.run_metadata(show=False)
            self.after(0, lambda: self.status("Analysis complete."))
        except Exception as e:                       # noqa
            self.after(0, lambda: self.status(f"Error: {e}"))

    # ------------------------------------------------------------ ELA tab
    def run_ela(self, show=True):
        img = self.original_bgr
        sweep = ela_sweep(img, qualities=(70, 85, int(self.ela_q.get()), 95))
        verdict = ela_verdict(sweep)
        best_map = sweep[int(self.ela_q.get())]["map"]
        annotated = overlay_suspicious(img, best_map)

        path = os.path.join(TMP, "ela_annotated.png")
        cv2.imwrite(path, annotated)
        cv2.imwrite(os.path.join(TMP, "ela_map.png"),
                    cv2.applyColorMap(best_map, cv2.COLORMAP_JET))

        lines = ["=== ERROR LEVEL ANALYSIS ===", "",
                 f"Verdict : {verdict}", "",
                 "Quality sweep (mean error per recompression level):"]
        for q, v in sweep.items():
            lines.append(f"  Q{q:>2}: mean={v['mean_error']:6.2f}  "
                         f"std={v['std_error']:6.2f}  max={v['max_error']:3d}")
        lines += ["", "Bright regions on the heatmap indicate inconsistent",
                  "compression artifacts — typical of localised editing.",
                  "", "Exhibit saved: ela_annotated.png"]
        self.results["ela"] = {"verdict": verdict, "sweep": sweep,
                               "exhibits": [("ELA annotated", path)]}
        if show:
            self.txt_forgery.delete("1.0", "end")
            self.txt_forgery.insert("1.0", "\n".join(lines))
            self._show_result_image(path)
            self.nb.select(self._tab_forgery)
        return sweep

    # -------------------------------------------------------- handwriting tab
    def run_handwriting(self, show=True):
        hm = HandwritingMetrics(self.original_bgr, dpi=300)
        profile = hm.full_profile()
        lines = ["=== HANDWRITING PROFILE (quantitative) ===", ""]
        for key, nice in [("zones", "Zone distribution (U/M/L)"),
                          ("slant", "Slant angle"),
                          ("baseline", "Baseline trend"),
                          ("pressure", "Pen pressure"),
                          ("stroke", "Stroke width"),
                          ("spacing", "Spacing"),
                          ("size", "Letter size")]:
            r = profile.get(key)
            if not r:
                continue
            detail = ", ".join(f"{k}={v}" for k, v in r.items()
                               if k not in ("ok", "interpretation"))
            lines.append(f"[{nice}] {detail}")
            lines.append(f"    -> {r['interpretation']}")
            lines.append("")
        if profile.get("flags"):
            lines.append("=== INVESTIGATIVE FLAGS ===")
            lines += [f"  ! {f}" for f in profile["flags"]]
        self.results["handwriting"] = profile
        if show:
            self.txt_handwriting.delete("1.0", "end")
            self.txt_handwriting.insert("1.0", "\n".join(lines))
            self.nb.select(self._tab_handwriting)
        return profile

    # ---------------------------------------------------------- forgery tab
    def run_forgery(self, show=True):
        img = self.original_bgr
        matches = copy_move_detection(img)
        cm_img = overlay_copy_move(img, matches)
        noise = noise_fingerprint(img)
        stats = pixel_statistics(img)
        path = os.path.join(TMP, "copy_move.png")
        cv2.imwrite(path, cm_img)

        lines = ["=== FORGERY / TAMPER DETECTION ===", "",
                 f"Copy-move (clone) matches found : {len(matches)}"]
        for (x, y, bw, bh, dx, dy, score) in matches[:12]:
            lines.append(f"  block ({x},{y},{bw}x{bh}) <- shifted "
                         f"({dx:+d},{dy:+d}) corr={score:.3f}")
        lines += ["", "=== SENSOR NOISE FINGERPRINT ===",
                  f"  residual std   : {noise['std']:.3f}",
                  f"  residual energy: {noise['energy']:.4f}",
                  f"  16x16 grid std : {noise['grid_std']:.3f} "
                  f"(high = uneven noise, possible splicing)",
                  "", "=== PIXEL STATISTICS ===",
                  f"  mean brightness : {stats['brightness_mean']:.1f}",
                  f"  brightness std  : {stats['brightness_std']:.1f}",
                  f"  ink coverage    : {stats['ink_coverage_pct']:.1f}%"]
        self.results["forgery"] = {"matches": matches, "noise": noise,
                                   "stats": stats,
                                   "exhibits": [("Copy-move overlay", path)]}
        if show:
            self.txt_forgery.delete("1.0", "end")
            self.txt_forgery.insert("1.0", "\n".join(lines))
            self._show_result_image(path)
            self.nb.select(self._tab_forgery)
        return matches

    # -------------------------------------------------------------- OCR tab
    def run_ocr(self):
        if self.original_bgr is None:
            messagebox.showwarning("No image", "Open an image first.")
            return
        self.status("OCR running…")
        threading.Thread(target=self._ocr_worker, daemon=True).start()

    def _ocr_worker(self):
        try:
            rgb = cv2.cvtColor(self.original_bgr, cv2.COLOR_BGR2RGB)
            # auto orientation
            osd = self.ocr_engine.detect_orientation(rgb)
            angle = osd.get("angle", 0) if osd.get("ok") else 0
            rgb = self.ocr_engine.deskew(rgb, angle)

            raw_langs = [s.strip().split("—")[0].strip()
                         for s in self.lang_var.get().split(",") if s.strip()]
            if osd.get("ok"):
                raw_langs = self.ocr_engine.infer_best_langs(
                    osd.get("script", "Latin"), raw_langs)
            result = self.ocr_engine.recognize(rgb, raw_langs)
            triage = self.ocr_engine.keyword_triage(result["text"], raw_langs)

            lines = [f"=== EXTRACTED TEXT (languages: {result['langs_used']}) ===",
                     f"Orientation : {osd.get('orientation', 'n/a')}° "
                     f"rotate={angle}° script={osd.get('script', 'n/a')}",
                     f"Confidence  : mean={result['mean_conf']}%  "
                     f"min={result['min_conf']}%", "",
                     result["text"].strip() or "(no text recognised)", "",
                     "=== KEYWORD TRIAGE ===",
                     f"Priority: {triage['priority']} (score {triage['score']})"]
            for cat, terms in triage["categories"].items():
                lines.append(f"  [{cat.upper()}] {', '.join(terms)}")
            self.results["ocr"] = result
            self.results["triage"] = triage
            self.after(0, lambda: self._show_ocr_result("\n".join(lines)))
        except Exception as e:                       # noqa
            self.after(0, lambda: self.status(f"OCR error: {e}"))

    def _show_ocr_result(self, text):
        self.txt_ocr.delete("1.0", "end")
        self.txt_ocr.insert("1.0", text)
        self.nb.select(self._tab_ocr)
        self.status("OCR complete.")

    # ---------------------------------------------------------- metadata tab
    def run_metadata(self, show=True):
        meta = full_metadata(self.path)
        lines = ["=== FILE & EXIF METADATA ===", ""]
        rows = [("Filename", meta["filename"]), ("Format", meta["format"]),
                ("Dimensions", meta["dimensions"]), ("DPI", meta["dpi"]),
                ("Size", f"{meta['size_bytes']:,} bytes"),
                ("Modified", meta["created_mtime"]),
                ("MD5", meta["hashes"]["md5"]),
                ("SHA-1", meta["hashes"]["sha1"]),
                ("SHA-256", meta["hashes"]["sha256"])]
        for k, v in meta["exif"].items():
            rows.append((f"EXIF:{k}", str(v)))
        lines += [f"  {k:<28}: {v}" for k, v in rows]
        self.results["metadata"] = meta
        if show:
            self.txt_metadata.delete("1.0", "end")
            self.txt_metadata.insert("1.0", "\n".join(lines))
            self.nb.select(self._tab_meta)
        return meta

    # ------------------------------------------------------------ conclusions
    def _conclusions(self) -> list:
        c = []
        ela = self.results.get("ela", {}).get("verdict", "")
        if "ANOMALOUS" in ela or "ELEVATED" in ela:
            c.append("ELA indicates localised compression anomalies — "
                     "region(s) may have been edited after original capture.")
        if self.results.get("forgery", {}).get("matches"):
            c.append("Copy-move analysis found duplicated regions — "
                     "possible cloned text/areas.")
        tri = self.results.get("triage", {})
        if tri.get("priority") in ("HIGH", "MEDIUM"):
            c.append(f"OCR keyword triage: {tri['priority']} priority "
                     f"(categories: {', '.join(tri['categories'])}) — "
                     "document content warrants immediate investigative review.")
        hw = self.results.get("handwriting", {})
        if hw.get("flags"):
            c.append("Handwriting profile flags: " +
                     "; ".join(hw["flags"]) + ".")
        if not c:
            c.append("No automated anomaly flags raised. Manual comparison "
                     "against known exemplars is recommended.")
        return c

    # ------------------------------------------------------------- exhibits
    def _collect_exhibits(self) -> list:
        ex = []
        for r in self.results.values():
            ex += r.get("exhibits", [])
        return ex

    # ------------------------------------------------------------- export
    def _export(self, pdf: bool):
        if not self.results:
            messagebox.showwarning("No analysis", "Run analysis first.")
            return
        self.results.setdefault("metadata",
                                full_metadata(self.path))
        data = {
            "case_id": os.path.splitext(os.path.basename(self.path))[0],
            "examiner": "Automated examiner",
            "metadata": self.results["metadata"],
            "ocr": self.results.get("ocr",
                                    {"text": "(OCR not run)",
                                     "langs_used": "-", "mean_conf": 0,
                                     "min_conf": 0}),
            "triage": self.results.get("triage", {}),
            "handwriting": self.results.get("handwriting", {}),
            "exhibits": self._collect_exhibits(),
            "conclusions": self._conclusions(),
        }
        ext = "pdf" if pdf else "html"
        out = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            filetypes=[(ext.upper(), f"*.{ext}")],
            initialfile=f"forensic_report_{datetime.now():%Y%m%d_%H%M}.{ext}")
        if not out:
            return
        try:
            (report_mod.build_pdf if pdf else report_mod.build_html)(data, out)
            self.status(f"Report saved: {out}")
        except Exception as e:                       # noqa
            messagebox.showerror("Export failed", str(e))

    def export_pdf(self):
        self._export(True)

    def export_html(self):
        self._export(False)

    def _show_result_image(self, path):
        img = Image.open(path)
        self.view_res.show_pil(img)

    def _about(self):
        messagebox.showinfo(
            "Handwriting Forensics Studio",
            "Forensic tool for questioned handwritten documents.\n\n"
            "Modules:\n"
            "• Error Level Analysis (ELA)\n"
            "• Handwriting metrics (zones, slant, baseline, pressure,\n"
            "  stroke width, spacing, size)\n"
            "• Copy-move / noise tamper detection\n"
            "• Multi-language OCR (Tesseract)\n"
            "• EXIF & hash forensics\n"
            "• PDF/HTML evidence reports\n\n"
            "Outputs are investigative aids and require review by a\n"
            "qualified forensic document examiner.")


if __name__ == "__main__":
    app = ForensicsApp()
    app.mainloop()
