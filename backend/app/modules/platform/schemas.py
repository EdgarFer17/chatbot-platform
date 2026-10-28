import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.platform.models import EnvironmentKind, KnowledgeStatus, SourceType, SyncJobStatus, SyncStatus


SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PlatformSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SlugMixin(BaseModel):
    slug: str = Field(min_length=2, max_length=80)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SLUG_PATTERN.fullmatch(normalized):
            raise ValueError("Use letras minúsculas, números e hífens")
        return normalized


class TenantCreate(SlugMixin):
    name: str = Field(min_length=2, max_length=160)


class TenantRead(PlatformSchema):
    id: uuid.UUID
    name: str
    slug: str
    active: bool
    monthly_message_limit: int
    created_at: datetime


class TenantQuotaUpdate(BaseModel):
    monthly_message_limit: int = Field(ge=1, le=10_000_000)


class UsageSummary(BaseModel):
    tenant_id: uuid.UUID
    environment_id: uuid.UUID | None
    period_start: datetime
    period_end: datetime
    interactions_used: int
    total_interactions_used: int
    monthly_limit: int
    remaining: int
    usage_percentage: float
    sessions_created: int


class EnvironmentCreate(SlugMixin):
    name: str = Field(min_length=2, max_length=120)
    kind: EnvironmentKind = EnvironmentKind.SANDBOX


class EnvironmentRead(PlatformSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    kind: EnvironmentKind
    active: bool
    created_at: datetime


class AssistantCreate(SlugMixin):
    name: str = Field(min_length=2, max_length=120)
    system_prompt: str = Field(default="", max_length=12000)


class AssistantRead(PlatformSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    name: str
    slug: str
    system_prompt: str
    active: bool
    created_at: datetime


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class ApiKeyRead(PlatformSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    name: str
    key_prefix: str
    active: bool
    created_at: datetime
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyRead):
    key: str


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=220)
    content: str = Field(min_length=20, max_length=100000)


class KnowledgeRead(PlatformSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    assistant_id: uuid.UUID
    source_id: uuid.UUID | None
    title: str
    content: str
    original_url: str | None
    mime_type: str | None
    checksum: str | None
    version_number: int
    is_current: bool
    status: KnowledgeStatus
    created_at: datetime
    published_at: datetime | None


class KnowledgeSummary(PlatformSchema):
    id: uuid.UUID
    source_id: uuid.UUID | None
    title: str
    content_preview: str
    original_url: str | None
    mime_type: str | None
    version_number: int
    is_current: bool
    status: KnowledgeStatus
    created_at: datetime
    published_at: datetime | None


class SourceCreate(BaseModel):
    name: str = Field(min_length=3, max_length=220)
    source_type: SourceType
    source_url: str | None = Field(default=None, max_length=2048)


class SourceRead(PlatformSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    environment_id: uuid.UUID
    assistant_id: uuid.UUID
    name: str
    source_type: SourceType
    source_url: str | None
    allowed_host: str | None
    sync_status: SyncStatus
    last_error: str | None
    created_at: datetime
    last_synced_at: datetime | None
    document_count: int = 0


class SyncResult(BaseModel):
    source_id: uuid.UUID
    discovered: int
    created: int
    unchanged: int
    failed: int


class SyncJobRead(PlatformSchema):
    id: uuid.UUID
    source_id: uuid.UUID
    status: SyncJobStatus
    discovered: int
    processed: int
    created: int
    unchanged: int
    failed: int
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AuditLogRead(PlatformSchema):
    id: uuid.UUID
    actor: str
    action: str
    resource_type: str
    resource_id: str | None
    tenant_id: uuid.UUID | None
    environment_id: uuid.UUID | None
    outcome: str
    created_at: datetime
