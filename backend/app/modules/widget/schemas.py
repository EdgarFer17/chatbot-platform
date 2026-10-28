import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse


class WidgetTokenCreate(BaseModel):
    assistant_id: uuid.UUID
    allowed_origin: str = Field(max_length=255)

    @field_validator("allowed_origin")
    @classmethod
    def validate_origin(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Informe apenas a origem, por exemplo https://faculdade.edu.br")
        return f"{parsed.scheme}://{parsed.netloc}".lower()


class WidgetTokenRead(BaseModel):
    token: str
    token_type: str = "Bearer"
    expires_at: datetime
    expires_in: int
