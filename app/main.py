import base64
import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .detector import analyze_frame

app = FastAPI(title="Veil", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"ok": True, "service": "Veil"}

@app.websocket("/ws/protect")
async def protect(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_text()
            try:
                raw = base64.b64decode(payload)
                frame = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    await websocket.send_json({"error":"invalid_frame"})
                    continue
                await websocket.send_json(analyze_frame(frame))
            except Exception as exc:
                await websocket.send_json({"error":str(exc)})
    except WebSocketDisconnect:
        pass
