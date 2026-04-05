import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import ALLOWED_ORIGINS
from database import init_db
from routers import capture, flows, alerts, reports, websocket
from routers.websocket import broadcast_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Initializing database...")
    await init_db()

    logger.info("Initializing services...")
    await capture.initialize_services()

    logger.info("Starting WebSocket broadcast loop...")
    broadcast_task = asyncio.create_task(broadcast_loop())

    logger.info("🚀 Traffic Classifier backend ready")
    yield

    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass
    logger.info("Backend shutdown complete")


app = FastAPI(
    title="AI Traffic Classifier",
    description="Real-time ML-based network traffic classification and monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(capture.router)
app.include_router(flows.router)
app.include_router(alerts.router)
app.include_router(reports.router)
app.include_router(websocket.router)


@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/", tags=["system"])
async def root():
    return {
        "name": "AI Traffic Classifier API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
