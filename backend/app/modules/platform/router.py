import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_database
from app.core.security import create_api_key, require_admin
from datetime import datetime, timezone

from app.modules.knowledge.ingestion import IngestionError, extract_document, validate_public_url
from app.modules.knowledge.chunking import split_content
from app.modules.knowledge.embeddings import generate_embeddings
from app.modules.platform.models import ApiKey, Assistant, AuditLog, Environment, KnowledgeChunk, KnowledgeDocument, KnowledgeSource, KnowledgeStatus, KnowledgeSyncJob, SourceType, SyncJobStatus, SyncStatus, Tenant
from app.modules.platform.schemas import ApiKeyCreate, ApiKeyCreated, ApiKeyRead, AssistantCreate, AssistantRead, AuditLogRead, EnvironmentCreate, EnvironmentRead, KnowledgeCreate, KnowledgeRead, KnowledgeSummary, SourceCreate, SourceRead, SyncJobRead, TenantCreate, TenantQuotaUpdate, TenantRead, UsageSummary
from app.modules.platform.usage import usage_summary

router = APIRouter(prefix="/admin", tags=["Administração"], dependencies=[Depends(require_admin)])


def audit(database: Session, action: str, resource_type: str, resource_id: uuid.UUID | str | None = None, tenant_id: uuid.UUID | None = None, environment_id: uuid.UUID | None = None) -> None:
    database.add(AuditLog(actor="operator", action=action, resource_type=resource_type, resource_id=str(resource_id) if resource_id else None, tenant_id=tenant_id, environment_id=environment_id, outcome="success"))


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(tenant_id: uuid.UUID | None = None, limit: int = 100, database: Session = Depends(get_database)) -> list[AuditLog]:
    query = select(AuditLog)
    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)
    return list(database.scalars(query.order_by(AuditLog.created_at.desc()).limit(min(max(limit, 1), 200))))


def commit_or_conflict(database: Session, message: str) -> None:
    try:
        database.commit()
    except IntegrityError as error:
        database.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from error


def get_tenant_or_404(database: Session, tenant_id: uuid.UUID) -> Tenant:
    tenant = database.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return tenant


def get_environment_or_404(database: Session, tenant_id: uuid.UUID, environment_id: uuid.UUID) -> Environment:
    environment = database.scalar(select(Environment).where(Environment.id == environment_id, Environment.tenant_id == tenant_id))
    if environment is None:
        raise HTTPException(status_code=404, detail="Ambiente não encontrado para este cliente")
    return environment


@router.post("/tenants", response_model=TenantRead, status_code=201)
def create_tenant(payload: TenantCreate, database: Session = Depends(get_database)) -> Tenant:
    tenant = Tenant(id=uuid.uuid4(), name=payload.name.strip(), slug=payload.slug)
    database.add(tenant)
    audit(database, "tenant.created", "tenant", tenant.id, tenant.id)
    commit_or_conflict(database, "Já existe um cliente com este identificador")
    database.refresh(tenant)
    return tenant


@router.get("/tenants", response_model=list[TenantRead])
def list_tenants(database: Session = Depends(get_database)) -> list[Tenant]:
    return list(database.scalars(select(Tenant).order_by(Tenant.name)))


@router.patch("/tenants/{tenant_id}/quota", response_model=TenantRead)
def update_tenant_quota(tenant_id: uuid.UUID, payload: TenantQuotaUpdate, database: Session = Depends(get_database)) -> Tenant:
    tenant = get_tenant_or_404(database, tenant_id)
    tenant.monthly_message_limit = payload.monthly_message_limit
    audit(database, "tenant.quota_updated", "tenant", tenant.id, tenant.id)
    database.commit()
    database.refresh(tenant)
    return tenant


@router.get("/tenants/{tenant_id}/usage", response_model=UsageSummary)
def get_tenant_usage(tenant_id: uuid.UUID, environment_id: uuid.UUID | None = None, database: Session = Depends(get_database)) -> dict:
    tenant = get_tenant_or_404(database, tenant_id)
    if environment_id:
        get_environment_or_404(database, tenant_id, environment_id)
    return usage_summary(database, tenant, environment_id)


@router.post("/tenants/{tenant_id}/environments", response_model=EnvironmentRead, status_code=201)
def create_environment(tenant_id: uuid.UUID, payload: EnvironmentCreate, database: Session = Depends(get_database)) -> Environment:
    get_tenant_or_404(database, tenant_id)
    environment = Environment(id=uuid.uuid4(), tenant_id=tenant_id, name=payload.name.strip(), slug=payload.slug, kind=payload.kind)
    database.add(environment)
    audit(database, "environment.created", "environment", environment.id, tenant_id, environment.id)
    commit_or_conflict(database, "Já existe um ambiente com este identificador para o cliente")
    database.refresh(environment)
    return environment


@router.get("/tenants/{tenant_id}/environments", response_model=list[EnvironmentRead])
def list_environments(tenant_id: uuid.UUID, database: Session = Depends(get_database)) -> list[Environment]:
    get_tenant_or_404(database, tenant_id)
    return list(database.scalars(select(Environment).where(Environment.tenant_id == tenant_id).order_by(Environment.name)))


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants", response_model=AssistantRead, status_code=201)
def create_assistant(tenant_id: uuid.UUID, environment_id: uuid.UUID, payload: AssistantCreate, database: Session = Depends(get_database)) -> Assistant:
    get_environment_or_404(database, tenant_id, environment_id)
    assistant = Assistant(id=uuid.uuid4(), tenant_id=tenant_id, environment_id=environment_id, name=payload.name.strip(), slug=payload.slug, system_prompt=payload.system_prompt.strip())
    database.add(assistant)
    audit(database, "assistant.created", "assistant", assistant.id, tenant_id, environment_id)
    commit_or_conflict(database, "Já existe um assistente com este identificador no ambiente")
    database.refresh(assistant)
    return assistant


@router.get("/tenants/{tenant_id}/environments/{environment_id}/assistants", response_model=list[AssistantRead])
def list_assistants(tenant_id: uuid.UUID, environment_id: uuid.UUID, database: Session = Depends(get_database)) -> list[Assistant]:
    get_environment_or_404(database, tenant_id, environment_id)
    return list(database.scalars(select(Assistant).where(Assistant.tenant_id == tenant_id, Assistant.environment_id == environment_id).order_by(Assistant.name)))


@router.post("/tenants/{tenant_id}/environments/{environment_id}/api-keys", response_model=ApiKeyCreated, status_code=201)
def issue_api_key(tenant_id: uuid.UUID, environment_id: uuid.UUID, payload: ApiKeyCreate, database: Session = Depends(get_database)) -> dict:
    get_environment_or_404(database, tenant_id, environment_id)
    raw_key, prefix, key_hash = create_api_key()
    api_key = ApiKey(id=uuid.uuid4(), tenant_id=tenant_id, environment_id=environment_id, name=payload.name.strip(), key_prefix=prefix, key_hash=key_hash)
    database.add(api_key)
    audit(database, "api_key.created", "api_key", api_key.id, tenant_id, environment_id)
    database.commit()
    database.refresh(api_key)
    response = ApiKeyRead.model_validate(api_key).model_dump()
    response["key"] = raw_key
    return response


@router.get("/tenants/{tenant_id}/environments/{environment_id}/api-keys", response_model=list[ApiKeyRead])
def list_api_keys(tenant_id: uuid.UUID, environment_id: uuid.UUID, database: Session = Depends(get_database)) -> list[ApiKey]:
    get_environment_or_404(database, tenant_id, environment_id)
    return list(database.scalars(select(ApiKey).where(ApiKey.tenant_id == tenant_id, ApiKey.environment_id == environment_id).order_by(ApiKey.created_at.desc())))


@router.delete("/tenants/{tenant_id}/environments/{environment_id}/api-keys/{api_key_id}", status_code=204)
def revoke_api_key(tenant_id: uuid.UUID, environment_id: uuid.UUID, api_key_id: uuid.UUID, database: Session = Depends(get_database)) -> None:
    api_key = database.scalar(select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.tenant_id == tenant_id, ApiKey.environment_id == environment_id))
    if api_key is None:
        raise HTTPException(status_code=404, detail="Chave não encontrada")
    api_key.active = False
    audit(database, "api_key.revoked", "api_key", api_key.id, tenant_id, environment_id)
    database.commit()


def get_assistant_or_404(database: Session, tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID) -> Assistant:
    assistant = database.scalar(select(Assistant).where(Assistant.id == assistant_id, Assistant.tenant_id == tenant_id, Assistant.environment_id == environment_id))
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistente não encontrado neste ambiente")
    return assistant


@router.get("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge", response_model=list[KnowledgeSummary])
def list_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, database: Session = Depends(get_database)) -> list[dict]:
    get_assistant_or_404(database, tenant_id, environment_id, assistant_id)
    documents = database.scalars(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.environment_id == environment_id, KnowledgeDocument.assistant_id == assistant_id).order_by(KnowledgeDocument.created_at.desc()))
    return [{"id": item.id, "source_id": item.source_id, "title": item.title, "content_preview": item.content[:240], "original_url": item.original_url, "mime_type": item.mime_type, "version_number": item.version_number, "is_current": item.is_current, "status": item.status, "created_at": item.created_at, "published_at": item.published_at} for item in documents]


@router.get("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge/{document_id}", response_model=KnowledgeRead)
def get_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, document_id: uuid.UUID, database: Session = Depends(get_database)) -> KnowledgeDocument:
    document = database.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.environment_id == environment_id, KnowledgeDocument.assistant_id == assistant_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")
    return document


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge", response_model=KnowledgeRead, status_code=201)
def create_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, payload: KnowledgeCreate, database: Session = Depends(get_database)) -> KnowledgeDocument:
    get_assistant_or_404(database, tenant_id, environment_id, assistant_id)
    document = KnowledgeDocument(tenant_id=tenant_id, environment_id=environment_id, assistant_id=assistant_id, title=payload.title.strip(), content=payload.content.strip())
    database.add(document)
    database.flush()
    audit(database, "knowledge.created", "knowledge_document", document.id, tenant_id, environment_id)
    database.commit()
    database.refresh(document)
    return document


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge/{document_id}/publish", response_model=KnowledgeRead)
def publish_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, document_id: uuid.UUID, database: Session = Depends(get_database)) -> KnowledgeDocument:
    document = database.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.environment_id == environment_id, KnowledgeDocument.assistant_id == assistant_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")
    if not document.is_current:
        raise HTTPException(409, "Revise e publique a versão mais recente deste documento")
    if document.source_id:
        previous = database.scalars(select(KnowledgeDocument).where(
            KnowledgeDocument.source_id == document.source_id,
            KnowledgeDocument.original_url == document.original_url,
            KnowledgeDocument.id != document.id,
            KnowledgeDocument.status == KnowledgeStatus.PUBLISHED,
        ))
        for item in previous:
            item.status = KnowledgeStatus.DRAFT
    database.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
    chunk_contents = split_content(document.content)
    chunk_vectors = generate_embeddings(chunk_contents)
    database.add_all([
        KnowledgeChunk(
            tenant_id=tenant_id,
            environment_id=environment_id,
            assistant_id=assistant_id,
            document_id=document.id,
            position=position,
            content=chunk_content,
            embedding=vector,
        )
        for position, (chunk_content, vector) in enumerate(zip(chunk_contents, chunk_vectors))
    ])
    document.status = KnowledgeStatus.PUBLISHED
    document.published_at = datetime.now(timezone.utc)
    audit(database, "knowledge.published", "knowledge_document", document.id, tenant_id, environment_id)
    database.commit()
    database.refresh(document)
    return document


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge/{document_id}/unpublish")
def unpublish_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, document_id: uuid.UUID, database: Session = Depends(get_database)):
    document = get_knowledge(tenant_id, environment_id, assistant_id, document_id, database)
    document.status = KnowledgeStatus.DRAFT
    operations = [document]
    if document.source_id:
        operations = database.scalars(select(KnowledgeDocument).where(KnowledgeDocument.source_id == document.source_id, KnowledgeDocument.original_url == document.original_url))
    for item in operations:
        item.status = KnowledgeStatus.DRAFT
    audit(database, "knowledge.unpublished", "knowledge_document", document.id, tenant_id, environment_id)
    database.commit()
    return {"ok": True}


@router.delete("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/knowledge/{document_id}", status_code=204)
def delete_knowledge(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, document_id: uuid.UUID, database: Session = Depends(get_database)) -> None:
    document = database.scalar(select(KnowledgeDocument).where(KnowledgeDocument.id == document_id, KnowledgeDocument.tenant_id == tenant_id, KnowledgeDocument.environment_id == environment_id, KnowledgeDocument.assistant_id == assistant_id))
    if document is None:
        raise HTTPException(status_code=404, detail="Conhecimento não encontrado")
    audit(database, "knowledge.deleted", "knowledge_document", document.id, tenant_id, environment_id)
    database.delete(document)
    database.commit()


def get_source_or_404(database: Session, tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, source_id: uuid.UUID) -> KnowledgeSource:
    source = database.scalar(select(KnowledgeSource).where(KnowledgeSource.id == source_id, KnowledgeSource.tenant_id == tenant_id, KnowledgeSource.environment_id == environment_id, KnowledgeSource.assistant_id == assistant_id))
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte não encontrada")
    return source


def source_response(database: Session, source: KnowledgeSource) -> dict:
    result = SourceRead.model_validate(source).model_dump()
    result["document_count"] = database.scalar(select(func.count(KnowledgeDocument.id)).where(KnowledgeDocument.source_id == source.id, KnowledgeDocument.is_current.is_(True))) or 0
    return result


@router.get("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources", response_model=list[SourceRead])
def list_sources(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, database: Session = Depends(get_database)) -> list[dict]:
    get_assistant_or_404(database, tenant_id, environment_id, assistant_id)
    sources = database.scalars(select(KnowledgeSource).where(KnowledgeSource.tenant_id == tenant_id, KnowledgeSource.environment_id == environment_id, KnowledgeSource.assistant_id == assistant_id).order_by(KnowledgeSource.created_at.desc()))
    return [source_response(database, source) for source in sources]


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources", response_model=SourceRead, status_code=201)
def create_source(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, payload: SourceCreate, database: Session = Depends(get_database)) -> dict:
    get_assistant_or_404(database, tenant_id, environment_id, assistant_id)
    if payload.source_type not in {SourceType.DOCUMENT_URL, SourceType.WEBSITE} or not payload.source_url:
        raise HTTPException(status_code=422, detail="Escolha documento por URL ou página sincronizável e informe o endereço")
    try:
        source_url, host = validate_public_url(payload.source_url)
    except IngestionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    source = KnowledgeSource(tenant_id=tenant_id, environment_id=environment_id, assistant_id=assistant_id, name=payload.name.strip(), source_type=payload.source_type, source_url=source_url, allowed_host=host)
    database.add(source)
    database.flush()
    audit(database, "source.created", "knowledge_source", source.id, tenant_id, environment_id)
    database.commit()
    database.refresh(source)
    return source_response(database, source)


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources/upload", response_model=SourceRead, status_code=201)
def upload_source(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, file: UploadFile = File(), database: Session = Depends(get_database)) -> dict:
    get_assistant_or_404(database, tenant_id, environment_id, assistant_id)
    from pathlib import PurePath
    if PurePath(file.filename or "").suffix.lower() not in {".pdf", ".docx", ".txt", ".html", ".htm"}:
        raise HTTPException(422, "Envie um arquivo PDF, DOCX, TXT ou HTML")
    data = file.file.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="O arquivo excede o limite de 20 MB")
    try:
        extracted = extract_document(data, file.content_type or "application/octet-stream", f"https://upload.local/{file.filename or 'documento'}", file.filename)
    except IngestionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    source = KnowledgeSource(tenant_id=tenant_id, environment_id=environment_id, assistant_id=assistant_id, name=file.filename or "Arquivo enviado", source_type=SourceType.FILE, sync_status=SyncStatus.READY, last_synced_at=datetime.now(timezone.utc))
    database.add(source)
    database.flush()
    database.add(KnowledgeDocument(tenant_id=tenant_id, environment_id=environment_id, assistant_id=assistant_id, source_id=source.id, title=extracted.title, content=extracted.content, mime_type=extracted.mime_type, checksum=extracted.checksum))
    audit(database, "source.uploaded", "knowledge_source", source.id, tenant_id, environment_id)
    database.commit()
    database.refresh(source)
    return source_response(database, source)


@router.post("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources/{source_id}/sync", response_model=SyncJobRead, status_code=202)
def sync_source(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, source_id: uuid.UUID, database: Session = Depends(get_database)) -> KnowledgeSyncJob:
    source = get_source_or_404(database, tenant_id, environment_id, assistant_id, source_id)
    if not source.source_url or not source.allowed_host:
        raise HTTPException(status_code=409, detail="Esta fonte não aceita sincronização por URL")
    active_job = database.scalar(select(KnowledgeSyncJob).where(KnowledgeSyncJob.source_id == source.id, KnowledgeSyncJob.status.in_([SyncJobStatus.PENDING, SyncJobStatus.RUNNING])))
    if active_job is not None:
        raise HTTPException(status_code=409, detail="Esta fonte já está sendo sincronizada")
    job = KnowledgeSyncJob(tenant_id=tenant_id, environment_id=environment_id, assistant_id=assistant_id, source_id=source.id)
    database.add(job)
    source.sync_status = SyncStatus.SYNCING
    database.flush()
    audit(database, "source.sync_requested", "knowledge_source", source.id, tenant_id, environment_id)
    database.commit()
    database.refresh(job)
    return job


@router.get("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources/{source_id}/sync-jobs/latest", response_model=SyncJobRead | None)
def latest_sync_job(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, source_id: uuid.UUID, database: Session = Depends(get_database)) -> KnowledgeSyncJob | None:
    get_source_or_404(database, tenant_id, environment_id, assistant_id, source_id)
    return database.scalar(select(KnowledgeSyncJob).where(KnowledgeSyncJob.source_id == source_id, KnowledgeSyncJob.tenant_id == tenant_id, KnowledgeSyncJob.environment_id == environment_id, KnowledgeSyncJob.assistant_id == assistant_id).order_by(KnowledgeSyncJob.created_at.desc()).limit(1))


@router.delete("/tenants/{tenant_id}/environments/{environment_id}/assistants/{assistant_id}/sources/{source_id}", status_code=204)
def delete_source(tenant_id: uuid.UUID, environment_id: uuid.UUID, assistant_id: uuid.UUID, source_id: uuid.UUID, database: Session = Depends(get_database)) -> None:
    source = get_source_or_404(database, tenant_id, environment_id, assistant_id, source_id)
    if database.scalar(select(KnowledgeSyncJob.id).where(KnowledgeSyncJob.source_id == source.id, KnowledgeSyncJob.status.in_([SyncJobStatus.PENDING, SyncJobStatus.RUNNING]))):
        raise HTTPException(409, "Aguarde a sincronização terminar antes de excluir a fonte")
    audit(database, "source.deleted", "knowledge_source", source.id, tenant_id, environment_id)
    database.delete(source)
    database.commit()
