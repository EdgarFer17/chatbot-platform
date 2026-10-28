import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("ADMIN_MASTER_KEY", "test-admin-key")
# Testes unitários nunca devem consumir uma credencial ou cota real do `.env`.
os.environ["GROQ_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_database
from app.main import app
from app.modules.platform import models  # noqa: F401


@pytest.fixture()
def database() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as database:
        yield database


@pytest.fixture()
def client(database: Session) -> TestClient:

    def override_database():
        yield database

    app.dependency_overrides[get_database] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
