from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_database
from app.core.security import ApiPrincipal, create_widget_token, require_api_key
from app.modules.platform.models import Assistant
from app.modules.widget.schemas import WidgetTokenCreate, WidgetTokenRead

router = APIRouter(prefix="/widget", tags=["Widget"])


@router.post("/tokens", response_model=WidgetTokenRead, status_code=201, summary="Emite um token temporário para o widget")
def issue_widget_token(payload: WidgetTokenCreate, principal: ApiPrincipal = Depends(require_api_key), database: Session = Depends(get_database)) -> WidgetTokenRead:
    assistant = database.scalar(select(Assistant).where(Assistant.id == payload.assistant_id, Assistant.tenant_id == principal.tenant_id, Assistant.environment_id == principal.environment_id, Assistant.active.is_(True)))
    if assistant is None:
        raise HTTPException(status_code=404, detail="Assistente não encontrado para esta integração")
    token, expires_at = create_widget_token(principal, assistant.id, payload.allowed_origin)
    return WidgetTokenRead(token=token, expires_at=datetime.fromtimestamp(expires_at, timezone.utc), expires_in=900)
