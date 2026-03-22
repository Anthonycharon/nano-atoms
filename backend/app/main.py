"""
FastAPI 应用入口。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_all_tables
# 导入所有模型，确保建表前 SQLModel 元数据已注册
import app.models  # noqa: F401

from app.api import auth, generation, projects, publish, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表。"""
    create_all_tables()
    yield


app = FastAPI(title="Nano Atoms API", version="0.1.0", lifespan=lifespan)

# CORS
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

# 注册路由
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(generation.router)
app.include_router(publish.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {"status": "ok"}
