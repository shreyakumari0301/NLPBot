"""NLP Conversation Intelligence — Channel Ingestion API entrypoint."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from src.admin.router import router as admin_router
from src.dashboard.router import router as dashboard_router
from src.ingestion import router as ingest_router
from src.live.router import router as live_router
from src.registry import init_db
from src.user_page import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Conversation Intake API",
    description="Channel Ingestion → Conversation Registry → Transcription → Normalization → Stored",
    lifespan=lifespan,
)
app.include_router(user_router)
app.include_router(ingest_router)
app.include_router(dashboard_router)
app.include_router(live_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok"}
