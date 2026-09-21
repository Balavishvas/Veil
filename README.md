# Veil

**Show the work. Hide the secrets.**

Veil is a local-first screen protection tool for presentations and recordings. It captures a selected screen/window, detects sensitive text with OCR and pattern matching, and masks only the exposed regions in a protected preview.

## Workflow

**Capture → Detect → Mask → Present**

The original desktop is never modified. Veil creates a protected canvas that can be recorded or opened in a separate presentation window.

## Protection

- Email addresses
- JWT-shaped tokens
- AWS access-key-shaped strings
- Phone numbers
- Card-like numbers
- Password/API key/secret/token assignment patterns
- Blur, redact, and pixelate modes
- Live protected preview
- WebM recording
- Protected presentation window
- Local FastAPI + OpenCV + Tesseract pipeline

## Run

Install Tesseract OCR and ensure `tesseract --version` works.

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

Click **START PROTECTED SESSION**, choose the screen/window to capture, and use the protected preview. **RECORD** records the masked canvas, not the raw screen.

## Important

This is an early prototype. OCR and pattern matching are heuristic and can miss sensitive content or create false positives. Do not treat Veil as a guarantee that every secret will be hidden.

Captured frames are sent to the local FastAPI process for OCR. There is no intentional third-party cloud video upload.

## Stack

Python · FastAPI · OpenCV · Tesseract OCR · WebSockets · Vanilla JavaScript · Canvas
