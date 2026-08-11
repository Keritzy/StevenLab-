"""
Quantitative handwriting metrics for forensic document examination.
Implements standard measurements (ENFSI BPM / graphology):
zones, slant, baseline, pen pressure, stroke width, spacing, size.
Every metric returns (value, interpretation) pairs suitable for reporting.
"""
from __future__ import annotations
import numpy as np
import cv2


class HandwritingMetrics:
    def __init__(self, img_bgr: np.ndarray, dpi: int = 300):
        self.bgr = img_bgr
        self.gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        self.dpi = dpi
        self._prepare()

    # ---------------------------------------------------------------- preproc
    def _prepare(self):
        # adaptive binarisation (ink = white on black)
        blur = cv2.medianBlur(self.gray, 5)
        self.bin = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 31, 15)
        # remove small specks
        self.bin = cv2.morphologyEx(
            self.bin, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        # connected components (characters/strokes)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            self.bin, connectivity=8)
        self.comps = [s for s in stats if s[4] > 25]  # filter noise

    def _px_to_mm(self, px: float) -> float:
        return px * 25.4 / max(self.dpi, 1)

    # ---------------------------------------------------------------- zones
    def zone_analysis(self) -> dict:
        """
        x-height estimation from component heights, then split into
        upper / middle / lower zones. Returns ratios of ink per zone.
        """
        if not self.comps:
            return {"ok": False}
        heights = [s[3] for s in self.comps]
        # middle zone ≈ most common small-component height (median of smalls)
        smalls = sorted(h for h in heights if h < np.percentile(heights, 60))
        x_height = float(np.median(smalls)) if smalls else 10.0

        ys, xe, ye = [], [], []
        for s in self.comps:
            x, y, w, h = s[0], s[1], s[2], s[3]
            ys.append(y); xe.append(x + w); ye.append(y + h)
        top, bottom = min(ys), max(ye)

        # per-component zone assignment
        upper_ink = mid_ink = lower_ink = 0
        for (x, y, w, h, a) in self.comps:
            mid_top = y + h * 0.45          # heuristic mid-band
            mid_bot = y + h * 0.85
            if h < x_height * 1.6:          # x-height letters -> middle zone
                mid_ink += a
            else:
                upper_ink += a * 0.35
                mid_ink += a * 0.50
                lower_ink += a * 0.15
        total = max(upper_ink + mid_ink + lower_ink, 1)
        r_up, r_mid, r_lo = (upper_ink / total, mid_ink / total, lower_ink / total)

        interp = (
            "Balanced three-zone profile (typical of regular writers)."
            if 0.10 <= r_up <= 0.45 and 0.35 <= r_mid <= 0.80 and r_lo <= 0.45
            else "Predominant upper zone: intellectualising / imagination traits. "
                 if r_up > 0.45
            else "Heavy lower zone: strong instincts, physical drive. "
                 if r_lo > 0.45
            else "Heavy middle zone: practical, here-and-now focus.")
        return {"ok": True, "x_height_mm": round(self._px_to_mm(x_height), 2),
                "upper": round(r_up, 3), "middle": round(r_mid, 3),
                "lower": round(r_lo, 3), "interpretation": interp}

    # ---------------------------------------------------------------- slant
    def slant_analysis(self) -> dict:
        """
        Shear-based slant estimation: rotate the ink horizontally via shear
        transforms at -45..+45 deg; the angle maximising horizontal projection
        energy equals the stroke slant (standard technique, cf. Hunt & Qi).
        """
        if not self.comps:
            return {"ok": False}
        h, w = self.bin.shape
        best_angle, best_energy = 0.0, -1.0
        for ang in np.arange(-45, 46, 3):
            M = np.float32([[1, -np.tan(np.radians(ang)), 0], [0, 1, 0]])
            sheared = cv2.warpAffine(self.bin, M, (w, h),
                                     flags=cv2.INTER_NEAREST)
            profile = sheared.sum(axis=0)
            energy = float((profile ** 2).sum())
            if energy > best_energy:
                best_energy, best_angle = energy, ang
        # refine locally
        for ang in np.arange(best_angle - 2, best_angle + 3, 0.5):
            M = np.float32([[1, -np.tan(np.radians(ang)), 0], [0, 1, 0]])
            sheared = cv2.warpAffine(self.bin, M, (w, h),
                                     flags=cv2.INTER_NEAREST)
            profile = sheared.sum(axis=0)
            energy = float((profile ** 2).sum())
            if energy > best_energy:
                best_energy, best_angle = energy, ang

        if best_angle > 15:
            interp = "Forward (rightward) slant — spontaneity, responsiveness, emotional expression"
        elif best_angle < -15:
            interp = "Backward (leftward) slant — reserve, guardedness, defensiveness"
        else:
            interp = "Vertical slant — self-control, independence, objectivity"
        return {"ok": True, "slant_deg": round(float(best_angle), 1),
                "interpretation": interp}

    # ---------------------------------------------------------------- baseline
    def baseline_analysis(self) -> dict:
        """
        Fit a line through the bottom pixels of each text line (via
        horizontal projection bands) — measures rise/fall of the writing.
        """
        if not self.comps:
            return {"ok": False}
        h = self.bin.shape[0]
        row_profile = self.bin.sum(axis=1)
        bands, in_band = [], False
        for y in range(h):
            active = row_profile[y] > 0
            if active and not in_band:
                start = y; in_band = True
            elif not active and in_band:
                bands.append((start, y)); in_band = False
        if in_band:
            bands.append((start, h - 1))
        bands = [b for b in bands if b[1] - b[0] > 5]

        # for each band, find bottom-most ink row centroid column-wise
        xs, ys = [], []
        for (y0, y1) in bands:
            band = self.bin[y0:y1 + 1]
            cols = np.where(band.sum(axis=0) > 0)[0]
            if len(cols) < 10:
                continue
            x = float(cols.mean())
            bottom_row = y1 - np.argmax(band[::-1].sum(axis=1) > 0)
            xs.append(x); ys.append(bottom_row)

        if len(xs) < 3:
            return {"ok": False}
        slope, intercept = np.polyfit(xs, ys, 1)
        # normalise slope as rise over writing width
        width = max(self.bin.shape[1], 1)
        rise = slope * width
        if abs(rise) < 12:
            interp = "Level baseline — emotional stability, self-discipline"
        elif rise < 0:
            interp = "Rising baseline — optimism, ambition, enthusiasm"
        else:
            interp = "Falling baseline — fatigue, pessimism, low energy state"
        return {"ok": True, "slope_px": round(float(slope), 4),
                "rise_px_over_width": round(float(rise), 1),
                "interpretation": interp}

    # ---------------------------------------------------------------- pressure
    def pressure_analysis(self) -> dict:
        """
        Pen pressure ≈ mean intensity of ink pixels (inverted so higher =
        darker/heavier). Reports heavy/medium/light classification.
        """
        ink = self.gray[self.bin > 0]
        if ink.size == 0:
            return {"ok": False}
        intensity = float(ink.mean())                     # 0=black ... 255=white
        pressure = 255.0 - intensity                      # higher = heavier ink
        if pressure > 150:
            interp = "Heavy pressure — strong emotional intensity, commitment, energy"
        elif pressure > 90:
            interp = "Medium pressure — balanced, adaptable temperament"
        else:
            interp = "Light pressure — sensitivity, speed, possible haste or fatigue"
        return {"ok": True, "pressure_0_255": round(pressure, 1),
                "ink_mean_intensity": round(intensity, 1),
                "interpretation": interp}

    # ---------------------------------------------------------------- stroke width
    def stroke_width(self) -> dict:
        """Median stroke thickness via distance transform on the skeleton."""
        dist = cv2.distanceTransform(self.bin, cv2.DIST_L2, 5)
        vals = dist[self.bin > 0]
        if vals.size == 0:
            return {"ok": False}
        med = float(np.median(vals)) * 2.0     # full width ≈ 2× half-width
        interp = ("Broad, heavy strokes — slow, deliberate writing"
                  if med > 2.5 else
                  "Fine, light strokes — rapid or light-touch writing")
        return {"ok": True, "stroke_width_px": round(med, 2),
                "stroke_width_mm": round(self._px_to_mm(med), 2),
                "interpretation": interp}

    # ---------------------------------------------------------------- spacing
    def spacing_analysis(self) -> dict:
        """Word/line spacing from vertical & horizontal projection gaps."""
        col_profile = self.bin.sum(axis=0)
        gaps, run = [], 0
        for v in col_profile:
            if v == 0:
                run += 1
            elif run > 0:
                gaps.append(run); run = 0
        if run:
            gaps.append(run)
        gaps = [g for g in gaps if g > 2]
        word_gap = float(np.median(gaps)) if gaps else 0.0

        row_profile = self.bin.sum(axis=1)
        row_gaps, run = [], 0
        for v in row_profile:
            if v == 0:
                run += 1
            elif run > 0:
                row_gaps.append(run); run = 0
        if run:
            row_gaps.append(run)
        line_gap = float(np.median([g for g in row_gaps if g > 4])) \
            if row_gaps else 0.0

        interp = ("Wide word spacing — desire for personal space, independence"
                  if word_gap > 30 else
                  "Narrow word spacing — sociability, possibly crowding/intrusion"
                  if 0 < word_gap <= 12 else
                  "Normal word spacing — conventional social balance")
        return {"ok": True, "word_gap_px": round(word_gap, 1),
                "line_gap_px": round(line_gap, 1),
                "word_gap_mm": round(self._px_to_mm(word_gap), 2),
                "interpretation": interp}

    # ---------------------------------------------------------------- size
    def size_analysis(self) -> dict:
        heights = [s[3] for s in self.comps]
        med_h = float(np.median(heights)) if heights else 0.0
        mm = self._px_to_mm(med_h)
        if mm >= 4.5:
            interp = "Large writing — extroversion, visibility-seeking, dominant presence"
        elif mm <= 2.2:
            interp = "Small writing — concentration, introspection, detail orientation"
        else:
            interp = "Medium writing — conventional, adaptable, well-adjusted"
        return {"ok": True, "median_char_height_mm": round(mm, 2),
                "interpretation": interp}

    # ---------------------------------------------------------------- aggregate
    def full_profile(self) -> dict:
        profile = {}
        for name, fn in [("zones", self.zone_analysis),
                         ("slant", self.slant_analysis),
                         ("baseline", self.baseline_analysis),
                         ("pressure", self.pressure_analysis),
                         ("stroke", self.stroke_width),
                         ("spacing", self.spacing_analysis),
                         ("size", self.size_analysis)]:
            r = fn()
            if r.get("ok"):
                profile[name] = r
        # composite risk flags for investigative triage
        flags = []
        if profile.get("pressure", {}).get("pressure_0_255", 0) > 160:
            flags.append("Extremely heavy pressure — possible intense emotional state")
        if profile.get("baseline", {}).get("rise_px_over_width", 0) > 60:
            flags.append("Sharply falling baseline — possible distress/fatigue")
        if profile.get("slant", {}).get("slant_deg", 0) < -25:
            flags.append("Strongly backward slant — possible concealment/guardedness")
        if profile.get("spacing", {}).get("word_gap_px", 99) == 0:
            flags.append("Absent word spacing — possible agitation/crowded writing")
        profile["flags"] = flags
        return profile
