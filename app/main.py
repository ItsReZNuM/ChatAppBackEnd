from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.core.config import settings
from app.api.routes import router as api_router
from app.socket.events import register_socket_events

# FastAPI app
fastapi_app = FastAPI(title="Chat Backend (FastAPI + Socket.IO)")

# CORS
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
fastapi_app.include_router(api_router, prefix="/api")

# Socket.IO with Redis message queue (good for scale)
mgr = socketio.AsyncRedisManager(settings.REDIS_URL)
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=origins or "*", client_manager=mgr)
register_socket_events(sio)

# Expose a single ASGI app (Socket.IO wrapping FastAPI)
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
