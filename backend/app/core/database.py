from sqlmodel import create_engine, Session, SQLModel
from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)


def create_all_tables() -> None:
    """启动时创建所有表（如不存在）。"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI 依赖注入：提供数据库 Session。"""
    with Session(engine) as session:
        yield session
