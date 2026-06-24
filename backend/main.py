"""FastAPI application entry point."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import admin, hitl, refinements, trips
from config import configure_langsmith, settings
from db.client import close_client, get_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SquadPlanner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api import trips, hitl, admin
from api.routes import auth
app.include_router(auth.router, prefix="/api")
app.include_router(trips.router, prefix="/api")
app.include_router(hitl.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.on_event("startup")
async def startup() -> None:
    db = get_database()
    try:
        await db.command("ping")
        logger.info("MongoDB connected (database=squadplanner).")
    except Exception as exc:
        logger.error("MongoDB connection failed: %s", exc)

    configure_langsmith()
    if settings.langchain_tracing_v2.lower() == "true":
        logger.info("LangSmith tracing enabled (project=%s).", settings.langchain_project)

    from agent.graph import initialize_graph

    await initialize_graph()
    logger.info("LangGraph orchestrator initialized.")


@app.on_event("shutdown")
async def shutdown() -> None:
    close_client()


@app.get("/health")
async def health():
    db = get_database()
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception:
        db_status = "unreachable"
    return {"status": "ok", "db": db_status}
