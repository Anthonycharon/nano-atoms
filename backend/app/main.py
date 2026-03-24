"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401
from app.api import assets, auth, generation, projects, publish, ws
from app.core.config import settings
from app.core.database import create_all_tables
from app.services.asset_storage import get_upload_root


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_all_tables()
    get_upload_root()
    yield


app = FastAPI(title="Nano Atoms API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=get_upload_root()), name="uploads")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(generation.router)
app.include_router(assets.router)
app.include_router(publish.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {"status": "ok"}
