import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

from kree.core.runtime import BUNDLE_DIR
from kree.mobile_bridge import KreeMobileBridge

PWA_DIR = BUNDLE_DIR / "pwa"

app = FastAPI(title="Kree PWA Companion API")

# Aegis Security: Restrict CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8765", "http://127.0.0.1:8765"], # Will be dynamically updated or allow specific
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    # Force no-cache for all PWA assets to guarantee immediate service worker updates
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Initialize the bridge to handle state and callbacks
bridge = KreeMobileBridge(port=8765)

@app.get("/status")
async def status():
    return {"status": "ok", "running": True}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await bridge.handle_websocket(websocket)

# Mount the static PWA files at the root
# Note: Mount this last so it doesn't override /ws or /status
if PWA_DIR.exists():
    app.mount("/", StaticFiles(directory=str(PWA_DIR), html=True), name="pwa")
else:
    logging.error(f"[KREE PWA] PWA directory not found at {PWA_DIR}")

def get_bridge():
    return bridge
