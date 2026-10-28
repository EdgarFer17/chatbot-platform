from datetime import datetime, timezone, timedelta
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_database
from app.core.security import ApiPrincipal, create_api_key, create_widget_token, decode_widget_token, require_admin
from app.modules.conversations.service import generate_response
from app.modules.platform import router as operations
from app.modules.platform.models import (ApiKey, Assistant, ConversationMessage, ConversationSession, Environment, EnvironmentKind,
    InstitutionConfig, KnowledgeDocument, KnowledgeSource, KnowledgeStatus, MessageRole, SessionStatus, Tenant, UsageEvent)
from app.modules.platform.schemas import SourceCreate
from app.modules.platform.usage import current_month_window, interactions_used

router = APIRouter(prefix="/admin/institution", tags=["FAFIC"], dependencies=[Depends(require_admin)])
public_router = APIRouter(prefix="/widget", tags=["Widget"])


def binding(database: Session):
    config = database.get(InstitutionConfig, 1)
    if config is None:
        raise HTTPException(409, "A configuração inicial da FAFIC ainda não foi concluída. Consulte o responsável pela instalação.")
    assistant = database.get(Assistant, config.assistant_id)
    if assistant is None:
        raise HTTPException(409, "Assistente institucional indisponível")
    return config, assistant


def scope(database: Session):
    _, assistant = binding(database)
    return dict(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, assistant_id=assistant.id, database=database)


def setup_institution(database: Session, assistant_id: uuid.UUID | None = None):
    """Explicit, idempotent setup; refuse ambiguous existing data."""
    existing = database.get(InstitutionConfig, 1)
    if existing:
        if assistant_id and existing.assistant_id != assistant_id:
            raise ValueError("Já existe uma vinculação. Nenhum registro foi alterado.")
        return existing
    if assistant_id:
        assistant = database.get(Assistant, assistant_id)
        if not assistant:
            raise ValueError("Assistente não encontrado")
        tenant = database.get(Tenant, assistant.tenant_id)
        if tenant.slug.lower() != "fafic" and tenant.name.strip().lower() != "fafic":
            raise ValueError("O assistente indicado não pertence à FAFIC")
    else:
        tenants = list(database.scalars(select(Tenant)))
        matches = [item for item in tenants if item.slug.lower() == "fafic" or item.name.strip().lower() == "fafic"]
        if len(matches) > 1 or (tenants and not matches):
            raise ValueError("Não foi possível identificar a FAFIC com segurança. Nenhum dado foi alterado.")
        tenant = matches[0] if matches else Tenant(name="FAFIC", slug="fafic")
        database.add(tenant)
        database.flush()
        environments = list(database.scalars(select(Environment).where(Environment.tenant_id == tenant.id)))
        if len(environments) > 1:
            raise ValueError("Há vários ambientes. Execute novamente com --assistant-id após revisar o inventário.")
        environment = environments[0] if environments else Environment(tenant_id=tenant.id, name="Institucional", slug="institucional", kind=EnvironmentKind.PRODUCTION)
        database.add(environment)
        database.flush()
        assistants = list(database.scalars(select(Assistant).where(Assistant.environment_id == environment.id)))
        if len(assistants) > 1:
            raise ValueError("Há vários assistentes. Execute novamente com --assistant-id após revisar o inventário.")
        assistant = assistants[0] if assistants else Assistant(tenant_id=tenant.id, environment_id=environment.id, name="Assistente FAFIC", slug="atendimento", system_prompt="Responda em português, com cordialidade e clareza, sobre a FAFIC.", active=False)
        database.add(assistant)
        database.flush()
    # Only the hash is retained. No permanent integration secret needs to leave the backend.
    _, prefix, digest = create_api_key()
    key = ApiKey(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, name="Widget institucional", key_prefix=prefix, key_hash=digest)
    database.add(key)
    database.flush()
    config = InstitutionConfig(id=1, assistant_id=assistant.id, api_key_id=key.id)
    database.add(config)
    database.commit()
    return config


@router.get("")
def institution_read(database: Session = Depends(get_database)):
    config, assistant = binding(database)
    return {"name": assistant.name, "active": assistant.active, "system_prompt": assistant.system_prompt,
        "welcome_message": config.welcome_message, "accent_color": config.accent_color,
        "unavailable_message": config.unavailable_message,
        "groq_configured": bool(settings.llm_provider == "groq" and settings.groq_api_key and settings.groq_model)}


class ControlUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    active: bool | None = None
    unavailable_message: str | None = Field(default=None, min_length=1, max_length=1000)


@router.get("/control")
def control_read(database: Session = Depends(get_database)):
    config, assistant = binding(database)
    return {"active": assistant.active, "unavailable_message": config.unavailable_message}


@router.patch("/control")
def control_update(payload: ControlUpdate, database: Session = Depends(get_database)):
    config, assistant = binding(database)
    if payload.active is not None:
        assistant.active = payload.active
    if payload.unavailable_message is not None:
        config.unavailable_message = payload.unavailable_message
    operations.audit(database, "institution.control_updated", "assistant", assistant.id, assistant.tenant_id, assistant.environment_id)
    database.commit()
    return control_read(database)


class InstitutionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=2, max_length=120)
    welcome_message: str = Field(min_length=1, max_length=1000)
    system_prompt: str = Field(max_length=12000)
    active: bool
    accent_color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


@router.patch("")
def institution_update(payload: InstitutionUpdate, database: Session = Depends(get_database)):
    config, assistant = binding(database)
    assistant.name, assistant.system_prompt, assistant.active = payload.name, payload.system_prompt, payload.active
    config.welcome_message, config.accent_color = payload.welcome_message, payload.accent_color
    operations.audit(database, "institution.updated", "assistant", assistant.id, assistant.tenant_id, assistant.environment_id)
    database.commit()
    return institution_read(database)


@router.get("/documents")
def institution_documents(database: Session = Depends(get_database)):
    return operations.list_knowledge(**scope(database))


@router.get("/documents/{document_id}")
def institution_document(document_id: uuid.UUID, database: Session = Depends(get_database)):
    from app.modules.platform.schemas import KnowledgeRead
    return KnowledgeRead.model_validate(operations.get_knowledge(document_id=document_id, **scope(database)))


@router.post("/documents/{document_id}/publish")
def institution_publish(document_id: uuid.UUID, database: Session = Depends(get_database)):
    operations.publish_knowledge(document_id=document_id, **scope(database))
    return {"ok": True}


@router.post("/documents/{document_id}/unpublish")
def institution_unpublish(document_id: uuid.UUID, database: Session = Depends(get_database)):
    return operations.unpublish_knowledge(document_id=document_id, **scope(database))


@router.delete("/documents/{document_id}", status_code=204)
def institution_delete_document(document_id: uuid.UUID, database: Session = Depends(get_database)):
    operations.delete_knowledge(document_id=document_id, **scope(database))


@router.get("/sources")
def institution_sources(database: Session = Depends(get_database)):
    return operations.list_sources(**scope(database))


@router.post("/sources", status_code=201)
def institution_add_source(payload: SourceCreate, database: Session = Depends(get_database)):
    return operations.create_source(payload=payload, **scope(database))


@router.post("/sources/upload", status_code=201)
def institution_upload(file: UploadFile = File(), database: Session = Depends(get_database)):
    return operations.upload_source(file=file, **scope(database))


@router.post("/sources/{source_id}/sync", status_code=202)
def institution_sync(source_id: uuid.UUID, database: Session = Depends(get_database)):
    from app.modules.platform.schemas import SyncJobRead
    return SyncJobRead.model_validate(operations.sync_source(source_id=source_id, **scope(database)))


@router.get("/sources/{source_id}/job")
def institution_job(source_id: uuid.UUID, database: Session = Depends(get_database)):
    from app.modules.platform.schemas import SyncJobRead
    job = operations.latest_sync_job(source_id=source_id, **scope(database))
    return SyncJobRead.model_validate(job) if job else None


@router.delete("/sources/{source_id}", status_code=204)
def institution_delete_source(source_id: uuid.UUID, database: Session = Depends(get_database)):
    operations.delete_source(source_id=source_id, **scope(database))


class HistoryMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=8000)


class PreviewMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    content: str = Field(min_length=1, max_length=8000)
    history: list[HistoryMessage] = Field(default_factory=list, max_length=6)


@router.post("/preview")
def institution_preview(payload: PreviewMessage, database: Session = Depends(get_database)):
    _, assistant = binding(database)
    return asdict(generate_response(database, assistant, payload.content, [(item.role, item.content) for item in payload.history]))


@router.get("/metrics")
def institution_metrics(database: Session = Depends(get_database)):
    config, assistant = binding(database)
    tenant = database.get(Tenant, assistant.tenant_id)
    start_month, end_month = current_month_window()
    used_month = interactions_used(database, assistant.tenant_id, assistant.environment_id)
    monthly_limit = tenant.monthly_message_limit if tenant else 1000

    sessions_total = database.scalar(
        select(func.count(ConversationSession.id)).where(ConversationSession.assistant_id == assistant.id)
    ) or 0
    sessions_month = database.scalar(
        select(func.count(ConversationSession.id)).where(
            ConversationSession.assistant_id == assistant.id,
            ConversationSession.created_at >= start_month,
            ConversationSession.created_at < end_month
        )
    ) or 0

    published_docs = database.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.assistant_id == assistant.id,
            KnowledgeDocument.status == KnowledgeStatus.PUBLISHED,
            KnowledgeDocument.is_current.is_(True)
        )
    ) or 0
    draft_docs = database.scalar(
        select(func.count(KnowledgeDocument.id)).where(
            KnowledgeDocument.assistant_id == assistant.id,
            KnowledgeDocument.status == KnowledgeStatus.DRAFT,
            KnowledgeDocument.is_current.is_(True)
        )
    ) or 0
    total_sources = database.scalar(
        select(func.count(KnowledgeSource.id)).where(KnowledgeSource.assistant_id == assistant.id)
    ) or 0

    avg_confidence = database.scalar(
        select(func.avg(ConversationMessage.confidence)).join(
            ConversationSession, ConversationSession.id == ConversationMessage.session_id
        ).where(
            ConversationSession.assistant_id == assistant.id,
            ConversationMessage.role == MessageRole.ASSISTANT,
            ConversationMessage.confidence.is_not(None)
        )
    )
    confidence_avg = round(float(avg_confidence), 2) if avg_confidence is not None else None

    total_user_messages = database.scalar(
        select(func.count(ConversationMessage.id)).join(
            ConversationSession, ConversationSession.id == ConversationMessage.session_id
        ).where(
            ConversationSession.assistant_id == assistant.id,
            ConversationMessage.role == MessageRole.USER
        )
    ) or 0

    now_utc = datetime.now(timezone.utc)
    fourteen_days_ago = now_utc - timedelta(days=13)
    recent_user_msgs = database.scalars(
        select(ConversationMessage).join(
            ConversationSession, ConversationSession.id == ConversationMessage.session_id
        ).where(
            ConversationSession.assistant_id == assistant.id,
            ConversationMessage.role == MessageRole.USER,
            ConversationMessage.created_at >= fourteen_days_ago
        )
    ).all()

    counts_by_day = {
        (fourteen_days_ago + timedelta(days=i)).strftime("%Y-%m-%d"): 0
        for i in range(14)
    }
    for m in recent_user_msgs:
        day_key = m.created_at.strftime("%Y-%m-%d")
        if day_key in counts_by_day:
            counts_by_day[day_key] += 1
        else:
            counts_by_day[day_key] = 1
    daily_messages = [{"date": k, "count": v} for k, v in sorted(counts_by_day.items())]

    recent_assistant_msgs = database.scalars(
        select(ConversationMessage).join(
            ConversationSession, ConversationSession.id == ConversationMessage.session_id
        ).where(
            ConversationSession.assistant_id == assistant.id,
            ConversationMessage.role == MessageRole.ASSISTANT,
            ConversationMessage.citations.is_not(None)
        ).order_by(ConversationMessage.created_at.desc()).limit(150)
    ).all()

    cited_counts: dict[str, int] = {}
    for msg in recent_assistant_msgs:
        if isinstance(msg.citations, list):
            for citation in msg.citations:
                if isinstance(citation, dict) and "title" in citation:
                    title = citation["title"]
                    cited_counts[title] = cited_counts.get(title, 0) + 1

    top_cited = sorted(
        [{"title": k, "count": v} for k, v in cited_counts.items()],
        key=lambda x: x["count"],
        reverse=True
    )[:6]

    return {
        "bot_active": assistant.active,
        "bot_name": assistant.name,
        "interactions_used": used_month,
        "monthly_limit": monthly_limit,
        "usage_percentage": round(min(100, used_month / monthly_limit * 100), 1) if monthly_limit else 0,
        "sessions_total": sessions_total,
        "sessions_month": sessions_month,
        "total_user_messages": total_user_messages,
        "published_documents": published_docs,
        "draft_documents": draft_docs,
        "total_sources": total_sources,
        "confidence_average": confidence_avg,
        "daily_messages": daily_messages,
        "top_cited_documents": top_cited,
    }


@router.get("/conversations")
def institution_conversations(
    limit: int = 50,
    offset: int = 0,
    database: Session = Depends(get_database),
):
    config, assistant = binding(database)
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)

    total_sessions = database.scalar(
        select(func.count(ConversationSession.id)).where(ConversationSession.assistant_id == assistant.id)
    ) or 0

    sessions = database.scalars(
        select(ConversationSession)
        .where(ConversationSession.assistant_id == assistant.id)
        .order_by(ConversationSession.updated_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()

    results = []
    for s in sessions:
        msgs = database.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == s.id)
            .order_by(ConversationMessage.created_at)
        ).all()
        first_user = next((m.content for m in msgs if m.role == MessageRole.USER), None)
        last_msg = msgs[-1] if msgs else None
        last_assistant = next((m for m in reversed(msgs) if m.role == MessageRole.ASSISTANT), None)

        results.append({
            "id": str(s.id),
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "message_count": len(msgs),
            "first_message": first_user[:140] if first_user else None,
            "last_message": last_msg.content[:140] if last_msg else None,
            "last_role": (last_msg.role.value if hasattr(last_msg.role, "value") else str(last_msg.role)) if last_msg else None,
            "confidence": last_assistant.confidence if last_assistant else None,
        })

    return {
        "total": total_sessions,
        "limit": limit,
        "offset": offset,
        "conversations": results,
    }


@router.get("/conversations/{session_id}")
def institution_conversation_detail(
    session_id: uuid.UUID,
    database: Session = Depends(get_database),
):
    config, assistant = binding(database)
    session = database.scalar(
        select(ConversationSession).where(
            ConversationSession.id == session_id,
            ConversationSession.assistant_id == assistant.id
        )
    )
    if session is None:
        raise HTTPException(404, "Conversa não encontrada")

    messages = database.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == session.id)
        .order_by(ConversationMessage.created_at)
    ).all()

    return {
        "id": str(session.id),
        "status": session.status.value if hasattr(session.status, "value") else str(session.status),
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "external_user_id": session.external_user_id,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                "content": m.content,
                "confidence": m.confidence,
                "citations": m.citations,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in messages
        ],
    }


class BootstrapRequest(BaseModel):
    resume_token: str | None = Field(default=None, max_length=4096)


@public_router.post("/bootstrap")
def institution_bootstrap(payload: BootstrapRequest, origin: str | None = Header(default=None), database: Session = Depends(get_database)):
    if not origin or origin not in settings.allowed_origins_list:
        raise HTTPException(403, "Este site não está autorizado a usar o assistente")
    config, assistant = binding(database)
    key = database.get(ApiKey, config.api_key_id)
    environment = database.get(Environment, assistant.environment_id)
    tenant = database.get(Tenant, assistant.tenant_id)
    if not key or not key.active or not environment.active or not tenant.active:
        raise HTTPException(503, config.unavailable_message)
    if not assistant.active:
        raise HTTPException(503, config.unavailable_message)
    if payload.resume_token:
        claims = decode_widget_token(payload.resume_token, origin, "resume")
        if claims.get("assistant_id") != str(assistant.id) or claims.get("api_key_id") != str(key.id):
            raise HTTPException(401, "Conversa expirada. Inicie uma nova conversa.")
        try:
            session = database.get(ConversationSession, uuid.UUID(claims["session_id"]))
        except (ValueError, KeyError, TypeError):
            session = None
        if not session or session.assistant_id != assistant.id or session.status != SessionStatus.ACTIVE:
            raise HTTPException(401, "Conversa expirada. Inicie uma nova conversa.")
    else:
        session = ConversationSession(tenant_id=assistant.tenant_id, environment_id=assistant.environment_id, assistant_id=assistant.id)
        database.add(session)
        database.commit()
    principal = ApiPrincipal(assistant.tenant_id, assistant.environment_id, key.id, assistant.id, "widget", session.id)
    token, expires = create_widget_token(principal, assistant.id, origin)
    resume, _ = create_widget_token(principal, assistant.id, origin, 86400, "resume")
    return {"token": token, "expires_at": expires, "resume_token": resume, "session_id": session.id,
        "name": assistant.name, "welcome_message": config.welcome_message, "accent_color": config.accent_color, "unavailable_message": config.unavailable_message}


@public_router.get("/appearance")
def institution_appearance(origin: str | None = Header(default=None), database: Session = Depends(get_database)):
    if not origin or origin not in settings.allowed_origins_list:
        raise HTTPException(403, "Este site não está autorizado a usar o assistente")
    config, assistant = binding(database)
    return {"name": assistant.name, "welcome_message": config.welcome_message, "accent_color": config.accent_color,
        "active": assistant.active, "unavailable_message": config.unavailable_message}
