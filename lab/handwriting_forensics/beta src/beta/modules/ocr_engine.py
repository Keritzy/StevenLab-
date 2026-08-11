"""
Multi-language OCR engine for questioned documents.
- Auto orientation & script detection (Tesseract OSD)
- Deskew before recognition
- Word-level confidence via image_to_data
- Investigative keyword triage (threat / ransom / suicide / coercion)
"""
from __future__ import annotations
import re
from collections import Counter

import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from PIL import Image

# language code -> display name (extend freely; install tesseract-ocr-<code>)
LANGUAGES = {
    "eng": "English", "ara": "Arabic", "hin": "Hindi", "urd": "Urdu",
    "ben": "Bengali", "pan": "Punjabi", "tam": "Tamil", "tel": "Telugu",
    "kan": "Kannada", "mal": "Malayalam", "mar": "Marathi", "guj": "Gujarati",
    "ori": "Odia", "nep": "Nepali", "deu": "German", "fra": "French",
    "spa": "Spanish", "ita": "Italian", "por": "Portuguese", "nld": "Dutch",
    "rus": "Russian", "ukr": "Ukrainian", "pol": "Polish", "ces": "Czech",
    "tur": "Turkish", "fas": "Persian", "chi_sim": "Chinese (Simplified)",
    "chi_tra": "Chinese (Traditional)", "jpn": "Japanese", "kor": "Korean",
    "tha": "Thai", "vie": "Vietnamese", "ind": "Indonesian", "msa": "Malay",
    "ell": "Greek", "heb": "Hebrew", "swe": "Swedish", "nor": "Norwegian",
    "dan": "Danish", "fin": "Finnish", "hun": "Hungarian", "ron": "Romanian",
    "bul": "Bulgarian", "srp": "Serbian", "hrv": "Croatian", "slv": "Slovenian",
    "slk": "Slovak", "lit": "Lithuanian", "lav": "Latvian", "est": "Estonian",
    "swa": "Swahili", "amh": "Amharic", "som": "Somali", "zul": "Zulu",
    "afr": "Afrikaans", "ara": "Arabic", "mon": "Mongolian", "kaz": "Kazakh",
    "aze": "Azerbaijani", "kat": "Georgian", "hye": "Armenian", "sin": "Sinhala",
}

# investigative keyword lexicons (lowercase; multi-language)
KEYWORD_LEXICON = {
    "threat": ["kill", "die", "death", "blood", "hurt", "attack", "gun", "bomb",
               "revenge", "destroy", "suffer", "قتل", "موت", "मार", "मौत", "杀", "殺",
               "töten", "mort", "muerte", "убить", "смерть"],
    "ransom": ["money", "pay", "cash", "ransom", "demand", "transfer", "bitcoin",
               "دollar", "पैसे", "فدیہ", "赎金", "贖金", "lösegeld", "rescate",
               "деньги", "выкуп", "भुगतान", "ادا"],
    "suicide": ["suicide", "kill myself", "end it", "goodbye", "can't go on",
                "no hope", "hate life", "आत्महत्या", "खुदकुशी", "خودکشی",
                "自杀", "自殺", "selbstmord", "suicidio", "самоубийство"],
    "coercion": ["or else", "if you", "unless", "warning", "last chance",
                 "وإلا", "अन्यथा", "否则", "sonst", "o si no", "иначе"],
    "fear": ["afraid", "scared", "terror", "fear", "panic", "nightmare",
             "خوف", "डर", "害怕", "angst", "miedo", "страх"],
    "anger": ["hate", "angry", "rage", "furious", "despise", "نفرت",
              "गुस्सा", "仇恨", "hass", "odio", "ненависть"],
}

RTL_SCRIPTS = {"Arabic", "Hebrew", "Persian"}


class OcrEngine:
    def __init__(self, tesseract_cmd: str | None = None):
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    # ------------------------------------------------------------------ OSD
    def detect_orientation(self, img_rgb: np.ndarray) -> dict:
        """Return rotation + script using Tesseract OSD (psm 0)."""
        try:
            d = pytesseract.image_to_osd(
                img_rgb, config="--psm 0 -c min_characters_to_try=5",
                output_type=Output.DICT)
            return {"ok": True, "angle": int(d["rotate"]),
                    "orientation": d.get("orientation", 0),
                    "script": d.get("script", "Latin"),
                    "script_conf": round(float(d.get("script_conf", 0)), 2)}
        except pytesseract.TesseractError:
            return {"ok": False, "error": "OSD failed (tessdata 'osd' missing)"}

    def deskew(self, img_rgb: np.ndarray, angle: int) -> np.ndarray:
        if angle == 0:
            return img_rgb
        h, w = img_rgb.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
        return cv2.warpAffine(img_rgb, m, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    # ------------------------------------------------------------ recognition
    def recognize(self, img_rgb: np.ndarray, langs: list[str],
                  psm: int = 3, enhance: bool = True) -> dict:
        """
        OCR with word-level confidence. `langs` e.g. ["eng", "hin"].
        Returns text, per-word data, and aggregate confidence stats.
        """
        # lightweight enhancement for handwritten/scanned docs
        if enhance:
            gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
            gray = cv2.resize(gray, None, fx=1.5, fy=1.5,
                              interpolation=cv2.INTER_CUBIC)
            gray = cv2.bilateralFilter(gray, 7, 60, 60)
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 41, 12)
            img_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

        lang_str = "+".join(langs if langs else ["eng"])
        config = f"--oem 3 --psm {psm}"
        text = pytesseract.image_to_string(img_rgb, lang=lang_str, config=config)
        data = pytesseract.image_to_data(
            img_rgb, lang=lang_str, config=config, output_type=Output.DICT)

        words = []
        for i, w in enumerate(data["text"]):
            w = w.strip()
            conf = float(data["conf"][i])
            if w and conf >= 0:
                words.append({
                    "word": w, "conf": conf,
                    "x": data["left"][i], "y": data["top"][i],
                    "w": data["width"][i], "h": data["height"][i],
                })
        confs = [wd["conf"] for wd in words] or [0.0]
        return {
            "text": text,
            "words": words,
            "mean_conf": round(float(np.mean(confs)), 1),
            "min_conf": round(float(np.min(confs)), 1),
            "langs_used": lang_str,
        }

    # ------------------------------------------------------------- keywords
    def keyword_triage(self, text: str, langs: list[str]) -> dict:
        low = text.lower()
        hits = {}
        for category, terms in KEYWORD_LEXICON.items():
            found = [t for t in terms if t.lower() in low]
            if found:
                hits[category] = found
        score = len(hits) * 10 + sum(min(len(v), 4) for v in hits.values())
        priority = ("HIGH" if score >= 30 else
                    "MEDIUM" if score >= 15 else
                    "LOW" if score > 0 else "NONE")
        return {"categories": hits, "score": score, "priority": priority}

    # ---------------------------------------------------------------- utils
    def available_languages(self) -> list[str]:
        try:
            return pytesseract.get_languages(config="")
        except Exception:
            return ["eng"]

    def infer_best_langs(self, script: str, user_langs: list[str]) -> list[str]:
        """Map detected script -> sensible language candidates."""
        mapping = {
            "Latin": ["eng"], "Arabic": ["ara", "urd", "fas"],
            "Devanagari": ["hin", "mar", "nep"], "Han": ["chi_sim", "jpn"],
            "Cyrillic": ["rus", "ukr", "bul"], "Hebrew": ["heb"],
            "Bengali": ["ben"], "Tamil": ["tam"], "Telugu": ["tel"],
            "Gujarati": ["guj"], "Gurmukhi": ["pan"], "Kannada": ["kan"],
            "Malayalam": ["mal"], "Oriya": ["ori"], "Sinhala": ["sin"],
            "Thai": ["tha"], "Korean": ["kor"], "Greek": ["ell"],
            "Armenian": ["hye"], "Georgian": ["kat"], "Ethiopic": ["amh"],
        }
        base = mapping.get(script, ["eng"])
        return list(dict.fromkeys(base + user_langs))
