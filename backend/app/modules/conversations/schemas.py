import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.platform.models import MessageRole, SessionStatus


class ConversationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SessionCreate(BaseModel):
    assistant_id: uuid.UUID
    external_user_id: str | None = Field(default=None, max_length=160)


class SessionRead(ConversationSchema):
    id: uuid.UUID
    assistant_id: uuid.UUID
    external_user_id: str | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageRead(ConversationSchema):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[dict] | None = None
    confidence: float | None = None
    created_at: datetime


class Citation(BaseModel):
    document_id: uuid.UUID
    title: str
    url: str | None
    excerpt: str


class MessageExchange(BaseModel):
    user_message: MessageRead
    assistant_message: MessageRead
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = 0.0
