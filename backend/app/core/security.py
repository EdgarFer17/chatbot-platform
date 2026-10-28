import hashlib
import hmac
import secrets
import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_database
from app.modules.platform.models import ApiKey, Environment, Tenant


def require_admin(x_admin_key: str = Header(alias="X-Admin-Key")) -> None:
    if not hmac.compare_digest(x_admin_key, settings.admin_master_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial administrativa inválida")


def create_api_key() -> tuple[str, str, str]:
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    raw_key = f"cbp_{prefix}_{secret}"
    return raw_key, prefix, hash_api_key(raw_key)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ApiPrincipal:
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    api_key_id: uuid.UUID
    assistant_id: uuid.UUID | None = None
    credential_kind: str = "api_key"
    session_id: uuid.UUID | None = None


def require_api_key(
    authorization: str | None = Header(default=None, alias="Authorization"),
    database: Session = Depends(get_database),
) -> ApiPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Informe a chave no formato Bearer")
    raw_key = authorization.removeprefix("Bearer ").strip()
    parts = raw_key.split("_", 2)
    if len(parts) != 3 or parts[0] != "cbp":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de API inválida")

    api_key = database.scalar(
        select(ApiKey)
        .join(Environment, Environment.id == ApiKey.environment_id)
        .join(Tenant, Tenant.id == ApiKey.tenant_id)
        .where(
            ApiKey.key_prefix == parts[1],
            ApiKey.key_hash == hash_api_key(raw_key),
            ApiKey.active.is_(True),
            Environment.active.is_(True),
            Tenant.active.is_(True),
        )
    )
    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chave de API inválida ou revogada")

    api_key.last_used_at = datetime.now(timezone.utc)
    database.commit()
    return ApiPrincipal(api_key.tenant_id, api_key.environment_id, api_key.id)


def create_widget_token(principal: ApiPrincipal, assistant_id: uuid.UUID, origin: str, ttl_seconds: int = 900, purpose: str = "conversation") -> tuple[str, int]:
    expires_at = int(time.time()) + ttl_seconds
    payload = {"tenant_id": str(principal.tenant_id), "environment_id": str(principal.environment_id), "api_key_id": str(principal.api_key_id), "assistant_id": str(assistant_id), "origin": origin, "exp": expires_at}
    payload.update(purpose=purpose, session_id=str(principal.session_id) if principal.session_id else None)
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(settings.jwt_secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return f"wgt_{encoded}.{signature}", expires_at


def decode_widget_token(raw: str, origin: str | None, purpose: str = "conversation") -> dict:
    try:
        if not raw.startswith("wgt_") or len(raw) > 4096:
            raise ValueError
        encoded, supplied = raw[4:].split(".", 1)
        expected = hmac.new(settings.jwt_secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ValueError
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if int(payload["exp"]) <= int(time.time()) or payload["origin"] != origin or payload.get("purpose", "conversation") != purpose:
            raise ValueError
        return payload
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        raise HTTPException(status_code=401, detail="Conversa expirada. Inicie uma nova conversa.") from error


def require_conversation_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
    origin: str | None = Header(default=None, alias="Origin"),
    database: Session = Depends(get_database),
) -> ApiPrincipal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Informe a credencial no formato Bearer")
    raw = authorization.removeprefix("Bearer ").strip()
    if raw.startswith("cbp_"):
        return require_api_key(authorization, database)
    if not raw.startswith("wgt_") or "." not in raw:
        raise HTTPException(status_code=401, detail="Credencial de conversa inválida")
    encoded, supplied_signature = raw.removeprefix("wgt_").split(".", 1)
    expected = hmac.new(settings.jwt_secret_key.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(supplied_signature, expected):
        raise HTTPException(status_code=401, detail="Token temporário inválido")
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        if int(payload["exp"]) <= int(time.time()) or origin != payload["origin"] or payload.get("purpose", "conversation") != "conversation":
            raise ValueError
        principal = ApiPrincipal(uuid.UUID(payload["tenant_id"]), uuid.UUID(payload["environment_id"]), uuid.UUID(payload["api_key_id"]), uuid.UUID(payload["assistant_id"]), "widget", uuid.UUID(payload["session_id"]) if payload.get("session_id") else None)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=401, detail="Token temporário expirado ou origem não autorizada") from error
    api_key = database.scalar(select(ApiKey).join(Environment, Environment.id == ApiKey.environment_id).join(Tenant, Tenant.id == ApiKey.tenant_id).where(ApiKey.id == principal.api_key_id, ApiKey.tenant_id == principal.tenant_id, ApiKey.environment_id == principal.environment_id, ApiKey.active.is_(True), Environment.active.is_(True), Tenant.active.is_(True)))
    if api_key is None:
        raise HTTPException(status_code=401, detail="A integração que emitiu este token não está mais ativa")
    return principal
