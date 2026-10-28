import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_database
from app.core.config import settings
from app.core.security import ApiPrincipal, require_conversation_principal
from app.modules.conversations.schemas import MessageCreate, MessageExchange, MessageRead, SessionCreate, SessionRead
from app.modules.conversations.service import generate_response, GenerationUnavailable
from app.modules.platform.models import Assistant, ConversationMessage, ConversationSession, InstitutionConfig, MessageRole, SessionStatus, Tenant, UsageEvent
from app.modules.platform.usage import interactions_used

router = APIRouter(prefix="/sessions", tags=["Conversas"])


def get_session_or_404(database: Session, principal: ApiPrincipal, session_id: uuid.UUID) -> ConversationSession:
    if principal.session_id and principal.session_id != session_id:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    conversation = database.scalar(
        select(ConversationSession).where(
            ConversationSession.id == session_id,
            ConversationSession.tenant_id == principal.tenant_id,
            ConversationSession.environment_id == principal.environment_id,
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if principal.assistant_id and principal.assistant_id != conversation.assistant_id:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return conversation


@router.post("", response_model=SessionRead, status_code=201)
def create_session(
    payload: SessionCreate,
    principal: ApiPrincipal = Depends(require_conversation_principal),
    database: Session = Depends(get_database),
) -> ConversationSession:
    if principal.session_id:
        raise HTTPException(status_code=403, detail="Este acesso já está vinculado a uma conversa")
    assistant = database.scalar(
        select(Assistant).where(
            Assistant.id == payload.assistant_id,
            Assistant.tenant_id == principal.tenant_id,
            Assistant.environment_id == principal.environment_id,
            Assistant.active.is_(True),
        )
    )
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistente não encontrado neste ambiente")
    if principal.assistant_id and principal.assistant_id != assistant.id:
        raise HTTPException(status_code=403, detail="O token temporário não permite este assistente")
    conversation = ConversationSession(
        tenant_id=principal.tenant_id,
        environment_id=principal.environment_id,
        assistant_id=assistant.id,
        external_user_id=payload.external_user_id.strip() if payload.external_user_id else None,
    )
    database.add(conversation)
    database.commit()
    database.refresh(conversation)
    return conversation


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: uuid.UUID,
    principal: ApiPrincipal = Depends(require_conversation_principal),
    database: Session = Depends(get_database),
) -> ConversationSession:
    return get_session_or_404(database, principal, session_id)


@router.get("/{session_id}/messages", response_model=list[MessageRead])
def list_messages(
    session_id: uuid.UUID,
    principal: ApiPrincipal = Depends(require_conversation_principal),
    database: Session = Depends(get_database),
) -> list[ConversationMessage]:
    get_session_or_404(database, principal, session_id)
    return list(database.scalars(select(ConversationMessage).where(ConversationMessage.session_id == session_id, ConversationMessage.tenant_id == principal.tenant_id).order_by(ConversationMessage.created_at)))


@router.post(
    "/{session_id}/messages",
    response_model=MessageExchange,
    status_code=201,
    responses={
        409: {"description": "A sessão está encerrada"},
        429: {"description": "A cota mensal da instituição foi atingida"},
    },
)
def send_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    principal: ApiPrincipal = Depends(require_conversation_principal),
    database: Session = Depends(get_database),
) -> MessageExchange:
    conversation = get_session_or_404(database, principal, session_id)
    if conversation.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A sessão está encerrada")
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="A mensagem não pode estar vazia")
    tenant = database.get(Tenant, principal.tenant_id)
    institution = database.get(InstitutionConfig, 1)
    if tenant is None or (not (institution and institution.assistant_id == conversation.assistant_id) and interactions_used(database, principal.tenant_id) >= tenant.monthly_message_limit):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="A cota mensal de mensagens desta instituição foi atingida")
    assistant = database.get(Assistant, conversation.assistant_id)
    unavailable = institution.unavailable_message if institution and institution.assistant_id == conversation.assistant_id else "Nosso bot está temporariamente indisponível. Tente novamente mais tarde."
    if assistant is None or not assistant.active:
        raise HTTPException(status_code=503, detail=unavailable)
    if institution and institution.assistant_id == conversation.assistant_id and settings.llm_provider == "groq" and not settings.groq_api_key:
        raise HTTPException(503, unavailable)
    recent_messages = list(database.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == conversation.id, ConversationMessage.tenant_id == principal.tenant_id, ConversationMessage.environment_id == principal.environment_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(settings.conversation_context_messages)
    ))
    history = [(message.role.value, message.content) for message in reversed(recent_messages)]
    user_message = ConversationMessage(tenant_id=principal.tenant_id, environment_id=principal.environment_id, session_id=conversation.id, role=MessageRole.USER, content=content)
    try:
        response = generate_response(database, assistant, content, history)
    except GenerationUnavailable:
        raise HTTPException(503, unavailable)
    assistant_message = ConversationMessage(tenant_id=principal.tenant_id, environment_id=principal.environment_id, session_id=conversation.id, role=MessageRole.ASSISTANT, content=response.content)
    assistant_message.citations = [asdict(citation) for citation in response.citations]
    assistant_message.confidence = response.confidence
    database.add_all([user_message, assistant_message])
    database.add(UsageEvent(tenant_id=principal.tenant_id, environment_id=principal.environment_id, assistant_id=assistant.id, api_key_id=principal.api_key_id, session_id=conversation.id, quantity=1))
    database.commit()
    database.refresh(user_message)
    database.refresh(assistant_message)
    return MessageExchange(user_message=MessageRead.model_validate(user_message), assistant_message=MessageRead.model_validate(assistant_message), citations=[{"document_id": citation.document_id, "title": citation.title, "url": citation.url, "excerpt": citation.excerpt} for citation in response.citations], confidence=response.confidence)


@router.post("/{session_id}/close", response_model=SessionRead)
def close_session(
    session_id: uuid.UUID,
    principal: ApiPrincipal = Depends(require_conversation_principal),
    database: Session = Depends(get_database),
) -> ConversationSession:
    conversation = get_session_or_404(database, principal, session_id)
    conversation.status = SessionStatus.CLOSED
    database.commit()
    database.refresh(conversation)
    return conversation
