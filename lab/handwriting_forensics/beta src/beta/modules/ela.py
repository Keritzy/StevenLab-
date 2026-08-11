"""
Error Level Analysis (ELA) engine.
Detects regions of an image with inconsistent JPEG compression artifacts,
which typically indicate splicing / localised re-editing.
"""
from __future__ import annotations
import io
import numpy as np
import cv2
from PIL import Image


def _recompress_jpeg(img_bgr: np.ndarray, quality: int) -> np.ndarray:
    """Re-encode a BGR image as JPEG at the given quality and decode back."""
    ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG re-encode failed")
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def ela_map(img_bgr: np.ndarray, quality: int = 90, scale: int = 15) -> np.ndarray:
    """
    Compute the ELA difference image.
    - Recompress at `quality`
    - absdiff between original and recompressed
    - amplify by `scale`, grayscale, CLAHE-enhanced
    Returns uint8 gray image. Bright areas == anomalous error level.
    """
    recompressed = _recompress_jpeg(img_bgr, quality)
    diff = cv2.absdiff(img_bgr, recompressed)
    ela = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY).astype(np.float32)
    ela = np.clip(ela * scale, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(16, 16))
    return clahe.apply(ela)


def ela_sweep(img_bgr: np.ndarray, qualities=(70, 85, 90, 95)) -> dict:
    """
    Sweep multiple recompression qualities (70-95).
    A genuine JPEG degrades *uniformly* at every level; tampered zones
    stay bright across the whole sweep. Returns per-quality maps + means.
    """
    results = {}
    for q in qualities:
        m = ela_map(img_bgr, quality=q)
        results[q] = {
            "map": m,
            "mean_error": float(m.mean()),
            "std_error": float(m.std()),
            "max_error": int(m.max()),
        }
    return results


def suspicious_regions(ela_gray: np.ndarray, threshold: float = 0.75) -> tuple:
    """
    Threshold the (0-255) ELA map at `threshold` * max value and return:
      (binary_mask, contours)
    Used to overlay red boxes over high-error zones.
    """
    thresh_val = max(int(ela_gray.max() * threshold), 40)
    _, mask = cv2.threshold(ela_gray, thresh_val, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # keep only meaningful blobs
    contours = [c for c in contours if cv2.contourArea(c) > 150]
    return mask, contours


def overlay_suspicious(img_bgr: np.ndarray, ela_gray: np.ndarray) -> np.ndarray:
    """Return annotated copy: suspicious regions boxed in red with a heatmap blend."""
    out = img_bgr.copy()
    mask, contours = suspicious_regions(ela_gray)
    heat = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)
    out = cv2.addWeighted(out, 0.45, heat, 0.55, 0)
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(out, (x, y), (x + w, y + h), (0, 0, 255), 2)
    return out


def ela_verdict(sweep: dict) -> str:
    """
    Heuristic verdict:
    - Uniformly low error across all qualities -> likely unmodified original
    - High error concentrated / std high -> potential tampering
    """
    means = [v["mean_error"] for v in sweep.values()]
    stds = [v["std_error"] for v in sweep.values()]
    spread = max(means) - min(means)
    if max(means) < 2.5:
        return "LOW ERROR LEVEL — image appears consistently compressed (likely untouched)"
    if spread < 1.5 and max(means) < 6:
        return "UNIFORM ERROR — minor global re-compression, no localised tampering evident"
    if max(stds) > 14:
        return "ANOMALOUS ERROR DISTRIBUTION — localised bright zones suggest possible splicing/editing"
    return "ELEVATED ERROR — further manual review recommended (heatmap + source history)"
