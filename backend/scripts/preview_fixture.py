"""Disposable local QA server. Never connects to the configured project database."""
import os
import tempfile
from pathlib import Path

temporary = tempfile.TemporaryDirectory(prefix="fafic-qa-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(temporary.name) / "preview.db").replace("\\", "/")
os.environ["GROQ_API_KEY"] = ""
os.environ["LLM_PROVIDER"] = "extractive"
os.environ["ADMIN_MASTER_KEY"] = "local-qa-only"
os.environ["JWT_SECRET_KEY"] = "local-qa-session-signing-only"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:3100,http://127.0.0.1:3100"
os.environ["APP_ENV"] = "test"

from app.core.database import Base, engine, SessionLocal
from app.modules.platform.institution import setup_institution
from app.modules.platform.models import Assistant, KnowledgeDocument, KnowledgeStatus
from app.main import app

Base.metadata.create_all(engine)
with SessionLocal() as database:
    config = setup_institution(database)
    assistant = database.get(Assistant, config.assistant_id)
    assistant.active = True
    database.add(KnowledgeDocument(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id,
        assistant_id=assistant.id, title="Documento fictício — validação local",
        content="Este é um documento fictício para teste local. A matrícula de demonstração ocorre no portal acadêmico de testes. Estas informações não são oficiais da FAFIC.", status=KnowledgeStatus.PUBLISHED))
    database.commit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8110)
