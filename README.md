# Veil

**Show the work. Hide the secrets.**

Veil is a local-first privacy layer for presentations and recordings. It captures a selected screen/window, performs a pre-flight scan, detects sensitive text with OCR and pattern matching, and masks exposed regions on a protected output canvas.

## The actual workflow

**Choose source → Pre-flight scan → Protected output → Share the Veil window**

The important rule is: **your audience must receive the protected output, not the original screen.** Veil does not currently intercept Zoom, Meet, Teams, or another app's native screen-share pipeline.

## What the prototype protects

- Email addresses
- JWT-shaped tokens
- AWS access-key-shaped strings
- Phone numbers
- Card-like numbers
- Password/API key/secret/token assignment patterns
- Blur, redact, and pixelate modes
- Pre-flight scan before protected mode
- Short temporal mask persistence to reduce flicker
- WebM recording from the protected canvas
- Separate protected presentation window
- Local FastAPI + OpenCV + Tesseract pipeline

## Run

Install Tesseract OCR and verify:

```bash
tesseract --version
```

Then:

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

1. Click **START PROTECTED SESSION**.
2. Select the screen/window to protect.
3. Wait for the **VEIL PREFLIGHT** scan.
4. Continue into protected mode.
5. Click **FULL VIEW** to open the protected output.
6. In Zoom/Meet/Teams, share **that Veil output window** — never the original source.

## Important safety limitation

This is still a prototype, not a guarantee of confidentiality. OCR and pattern matching are heuristic and can miss sensitive content or produce false positives. The browser capture API also cannot transparently replace another application's native screen-share source.

For real confidential meetings, verify the protected output before sharing and use test/fake secrets first.

## Stack

Python · FastAPI · OpenCV · Tesseract OCR · WebSockets · Vanilla JavaScript · Canvas
