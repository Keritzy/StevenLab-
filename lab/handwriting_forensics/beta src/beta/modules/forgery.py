"""
Additional forgery detection: copy-move/clone detection, noise fingerprinting,
and basic pixel statistics for document forensics.
"""
from __future__ import annotations
import numpy as np
import cv2


def copy_move_detection(img_bgr: np.ndarray,
                        block: int = 16,
                        max_offset: int = 80,
                        tolerance: float = 0.9) -> list:
    """
    Block-based copy-move detection.
    Overlapping blocks are compared with zero-normalised correlation;
    blocks that match with a translation within max_offset (but not
    self-matches) are flagged. Returns list of (x, y, w, h, dx, dy, score).
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    feats, coords = [], []
    step = block // 2
    for y in range(0, h - block + 1, step):
        for x in range(0, w - block + 1, step):
            blk = gray[y:y + block, x:x + block]
            mean = blk.mean()
            std = blk.std() + 1e-6
            feats.append(((blk - mean) / std).ravel())
            coords.append((x, y))
    feats = np.asarray(feats, dtype=np.float32)
    coords = np.asarray(coords, dtype=np.int32)
    matches = []
    for i, (f, (x1, y1)) in enumerate(zip(feats, coords)):
        # correlation with all blocks
        corr = feats @ f / feats.shape[1]
        best = np.argsort(corr)[::-1][:3]
        for j in best:
            if corr[j] < tolerance or j == i:
                continue
            x2, y2 = coords[j]
            dx, dy = x2 - x1, y2 - y1
            if max(abs(dx), abs(dy)) > max_offset:      # far apart = not a real copy
                continue
            if abs(dx) + abs(dy) < 2:                   # adjacent/self block
                continue
            matches.append((x1, y1, block, block, dx, dy, float(corr[j])))
    # de-duplicate symmetric pairs
    seen, uniq = set(), []
    for m in sorted(matches, key=lambda t: -t[6]):
        key = (m[0] // block, m[1] // block, m[4] // block, m[5] // block)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(m)
    return uniq


def overlay_copy_move(img_bgr: np.ndarray, matches: list) -> np.ndarray:
    """Draw matched clone-region pairs in green."""
    out = img_bgr.copy()
    for (x, y, bw, bh, dx, dy, score) in matches:
        cv2.rectangle(out, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
        cv2.rectangle(out, (x + dx, y + dy), (x + dx + bw, y + dy + bh), (0, 200, 0), 2)
        cv2.line(out, (x, y), (x + dx, y + dy), (255, 0, 255), 1)
    return out


def noise_fingerprint(img_bgr: np.ndarray) -> dict:
    """
    Residual noise (image - gaussian smooth) statistics.
    Spliced regions usually have different noise energy than the rest.
    Returns global stats + a 16x16 noise-energy heatmap grid.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    smooth = cv2.GaussianBlur(gray, (0, 0), sigmaX=3)
    residual = gray - smooth
    h, w = residual.shape
    gy, gx = 16, 16
    ch, cw = h // gy, w // gx
    grid = np.zeros((gy, gx), dtype=np.float32)
    for i in range(gy):
        for j in range(gx):
            cell = residual[i * ch:(i + 1) * ch, j * cw:(j + 1) * cw]
            grid[i, j] = float(np.std(cell))
    return {
        "mean": float(residual.mean()),
        "std": float(residual.std()),
        "energy": float((residual ** 2).mean()),
        "grid": grid,
        "grid_mean": float(grid.mean()),
        "grid_std": float(grid.std()),
    }


def pixel_statistics(img_bgr: np.ndarray) -> dict:
    """Basic statistics for the report: brightness, contrast, ink coverage."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    ink = np.sum(hist[:128]) / gray.size * 100.0        # darker-than-mid pixels
    return {
        "brightness_mean": float(gray.mean()),
        "brightness_std": float(gray.std()),
        "ink_coverage_pct": float(ink),
        "min": int(gray.min()),
        "max": int(gray.max()),
        "histogram": hist.astype(np.int32),
    }
