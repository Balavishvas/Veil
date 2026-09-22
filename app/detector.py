import re
from typing import Any

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "phone": re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)"),
    "card": re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)"),
    "secret": re.compile(r"(?i)\b(api[_ -]?key|secret|access[_ -]?token|private[_ -]?key|password|passwd)\b\s*[:=]\s*\S{4,}"),
}
LABELS = {
    "email": "EMAIL",
    "jwt": "JWT / TOKEN",
    "aws_key": "AWS KEY",
    "phone": "PHONE",
    "card": "CARD-LIKE NUMBER",
    "secret": "SECRET / CREDENTIAL",
}


def _ocr(frame: np.ndarray) -> tuple[str, list[dict[str, int]]]:
    """OCR an enlarged, high-contrast frame and keep word coordinates."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    scale = 1.6 if max(frame.shape[:2]) < 1800 else 1.25
    enlarged = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    enlarged = cv2.threshold(enlarged, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    data = pytesseract.image_to_data(
        enlarged,
        config="--oem 3 --psm 6",
        output_type=Output.DICT,
    )

    words = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        try:
            confidence = float(data["conf"][i])
        except (ValueError, TypeError):
            confidence = -1
        if text and confidence >= 20:
            words.append({
                "text": text,
                "left": int(data["left"][i] / scale),
                "top": int(data["top"][i] / scale),
                "width": max(1, int(data["width"][i] / scale)),
                "height": max(1, int(data["height"][i] / scale)),
            })
    return " ".join(w["text"] for w in words), words


def analyze_frame(frame: np.ndarray) -> dict[str, Any]:
    full_text, words = _ocr(frame)
    boxes = []

    # Match both the normal OCR stream and a compact stream so values split
    # by OCR whitespace/punctuation are still easier to recognize.
    streams = [(full_text, words)]
    compact = re.sub(r"\s+", "", full_text)
    if compact != full_text:
        streams.append((compact, words))

    for kind, pattern in PATTERNS.items():
        for text_stream, stream_words in streams:
            for match in pattern.finditer(text_stream):
                selected = []
                if text_stream is full_text:
                    cursor = 0
                    for word in stream_words:
                        pos = full_text.find(word["text"], cursor)
                        if pos < 0:
                            continue
                        end = pos + len(word["text"])
                        cursor = end
                        if end > match.start() and pos < match.end():
                            selected.append(word)
                else:
                    # Compact stream has no stable character-to-word mapping;
                    # use OCR text containment as a safe fallback.
                    target = match.group(0).lower()
                    for word in stream_words:
                        if word["text"].lower() in target or target in word["text"].lower():
                            selected.append(word)

                if selected:
                    x1 = min(w["left"] for w in selected)
                    y1 = min(w["top"] for w in selected)
                    x2 = max(w["left"] + w["width"] for w in selected)
                    y2 = max(w["top"] + w["height"] for w in selected)
                    pad_x = max(6, int((x2 - x1) * 0.08))
                    pad_y = max(4, int((y2 - y1) * 0.35))
                    boxes.append({
                        "kind": kind,
                        "label": LABELS[kind],
                        "x": max(0, x1 - pad_x),
                        "y": max(0, y1 - pad_y),
                        "w": min(frame.shape[1] - max(0, x1 - pad_x), x2 - x1 + pad_x * 2),
                        "h": min(frame.shape[0] - max(0, y1 - pad_y), y2 - y1 + pad_y * 2),
                    })

    unique = []
    for box in boxes:
        duplicate = False
        for old in unique:
            xa = max(box["x"], old["x"])
            ya = max(box["y"], old["y"])
            xb = min(box["x"] + box["w"], old["x"] + old["w"])
            yb = min(box["y"] + box["h"], old["y"] + old["h"])
            inter = max(0, xb - xa) * max(0, yb - ya)
            union = box["w"] * box["h"] + old["w"] * old["h"] - inter
            if union and inter / union > 0.55:
                duplicate = True
                break
        if not duplicate:
            unique.append(box)

    risk = min(100, len(unique) * 32)
    return {
        "risk": risk,
        "status": "PROTECTED" if unique else "CLEAR",
        "findings": unique,
        "count": len(unique),
        "frame_width": int(frame.shape[1]),
        "frame_height": int(frame.shape[0]),
    }
