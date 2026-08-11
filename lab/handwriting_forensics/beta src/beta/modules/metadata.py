"""
Metadata & file-level forensics: EXIF, hashes, DPI, hidden data.
"""
from __future__ import annotations
import hashlib
import os
from datetime import datetime
from PIL import Image, ExifTags


def file_hashes(path: str) -> dict:
    h = {alg: hashlib.new(alg) for alg in ("md5", "sha1", "sha256")}
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            for d in h.values():
                d.update(chunk)
    return {alg: d.hexdigest() for alg, d in h.items()}


def extract_exif(img: Image.Image) -> dict:
    out = {}
    exif = img.getexif()
    if not exif:
        return out
    for k, v in exif.items():
        name = ExifTags.TAGS.get(k, str(k))
        if isinstance(v, bytes):
            try:
                v = v.decode("utf-8", "replace")
            except Exception:
                v = repr(v)
        out[name] = v
    # GPS block
    gps = exif.get_ifd(0x8825)
    if gps:
        gps_names = ExifTags.GPSTAGS
        gps_dict = {}
        for k, v in gps.items():
            name = gps_names.get(k, k)
            if isinstance(v, tuple) and len(v) == 3 and isinstance(v[0], tuple):
                v = (v[0][0] / v[0][1], v[1][0] / v[1][1], v[2][0] / v[2][1])
            gps_dict[str(name)] = v
        if "GPSLatitude" in gps_dict and "GPSLongitude" in gps_dict:
            lat = _dms_to_dec(gps_dict["GPSLatitude"])
            lon = _dms_to_dec(gps_dict["GPSLongitude"])
            if gps_dict.get("GPSLatitudeRef") == "S":
                lat = -lat
            if gps_dict.get("GPSLongitudeRef") == "W":
                lon = -lon
            out["GPS"] = f"{lat:.6f}, {lon:.6f}"
            out["GeoHint"] = _reverse_hint(lat, lon)
    return out


def _dms_to_dec(t: tuple) -> float:
    return t[0] + t[1] / 60.0 + t[2] / 3600.0


def _reverse_hint(lat: float, lon: float) -> str:
    regions = [
        (35.0, 139.69, "Tokyo/Japan"), (28.61, 77.20, "Delhi/India"),
        (19.07, 72.87, "Mumbai/India"), (51.50, -0.12, "London/UK"),
        (40.71, -74.00, "New York/USA"), (37.77, -122.41, "San Francisco/USA"),
        (52.52, 13.40, "Berlin/Germany"), (48.85, 2.35, "Paris/France"),
        (-33.86, 151.20, "Sydney/AU"), (1.35, 103.81, "Singapore"),
        (25.20, 55.27, "Dubai/UAE"), (30.04, 31.23, "Cairo/Egypt"),
    ]
    best, best_d = None, 1e9
    for rlat, rlon, name in regions:
        d = (rlat - lat) ** 2 + (rlon - lon) ** 2
        if d < best_d:
            best_d, best = d, name
    return best if best_d < 10 else "Not in known city list"


def full_metadata(path: str) -> dict:
    st = os.stat(path)
    img = Image.open(path)
    exif = extract_exif(img)
    return {
        "filename": os.path.basename(path),
        "size_bytes": st.st_size,
        "format": img.format,
        "mode": img.mode,
        "dimensions": f"{img.width} x {img.height}",
        "dpi": img.info.get("dpi", "not set"),
        "created_mtime": datetime.fromtimestamp(st.st_mtime).isoformat(),
        "hashes": file_hashes(path),
        "exif": exif,
        "icc": bool(img.info.get("icc_profile")),
    }
