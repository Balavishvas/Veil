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
LABELS = {"email":"EMAIL","jwt":"JWT / TOKEN","aws_key":"AWS KEY","phone":"PHONE","card":"CARD-LIKE NUMBER","secret":"SECRET / CREDENTIAL"}

def analyze_frame(frame: np.ndarray) -> dict[str, Any]:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    data = pytesseract.image_to_data(rgb, config="--psm 6", output_type=Output.DICT)
    words = []
    for i, raw in enumerate(data["text"]):
        text = raw.strip()
        if text:
            words.append({"text":text,"left":int(data["left"][i]),"top":int(data["top"][i]),"width":int(data["width"][i]),"height":int(data["height"][i])})
    full_text = " ".join(w["text"] for w in words)
    boxes = []
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(full_text):
            selected = []
            cursor = 0
            for word in words:
                pos = full_text.find(word["text"], cursor)
                if pos < 0:
                    continue
                end = pos + len(word["text"])
                cursor = end
                if end > match.start() and pos < match.end():
                    selected.append(word)
            if selected:
                x1=min(w["left"] for w in selected); y1=min(w["top"] for w in selected)
                x2=max(w["left"]+w["width"] for w in selected); y2=max(w["top"]+w["height"] for w in selected)
                boxes.append({"kind":kind,"label":LABELS[kind],"x":x1,"y":y1,"w":max(1,x2-x1),"h":max(1,y2-y1)})
    unique=[]
    for box in boxes:
        duplicate=False
        for old in unique:
            xa=max(box["x"],old["x"]); ya=max(box["y"],old["y"])
            xb=min(box["x"]+box["w"],old["x"]+old["w"]); yb=min(box["y"]+box["h"],old["y"]+old["h"])
            inter=max(0,xb-xa)*max(0,yb-ya)
            union=box["w"]*box["h"]+old["w"]*old["h"]-inter
            if union and inter/union > .65:
                duplicate=True; break
        if not duplicate: unique.append(box)
    risk=min(100,len(unique)*32)
    return {"risk":risk,"status":"PROTECTED" if unique else "CLEAR","findings":unique,"count":len(unique),"frame_width":int(frame.shape[1]),"frame_height":int(frame.shape[0])}
