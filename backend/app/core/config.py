from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Chatbot Platform"
    app_env: str = "development"
    app_version: str = "1.0.0-rc.1"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://chatbot:change-me@localhost:5432/chatbot_platform"
    jwt_secret_key: str = "development-only-change-me"
    admin_master_key: str = "development-admin-change-me"
    llm_provider: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    llm_max_output_tokens: int = 700
    llm_timeout_seconds: float = 35
    llm_reasoning_effort: str = "low"
    allowed_origins: str = "http://localhost:3000"
    conversation_context_messages: int = 6
    conversation_context_characters: int = 8000
    sql_echo: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"development", "test", "staging", "production"}:
            raise ValueError("APP_ENV inválido")
        return normalized

    @field_validator("llm_max_output_tokens")
    @classmethod
    def validate_output_limit(cls, value: int) -> int:
        if not 100 <= value <= 4000:
            raise ValueError("LLM_MAX_OUTPUT_TOKENS deve estar entre 100 e 4000")
        return value

    @field_validator("llm_timeout_seconds")
    @classmethod
    def validate_llm_timeout(cls, value: float) -> float:
        if not 5 <= value <= 120:
            raise ValueError("LLM_TIMEOUT_SECONDS deve estar entre 5 e 120")
        return value

    @field_validator("llm_reasoning_effort")
    @classmethod
    def validate_reasoning_effort(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "high"}:
            raise ValueError("LLM_REASONING_EFFORT deve ser low, medium ou high")
        return normalized

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @field_validator("conversation_context_messages")
    @classmethod
    def validate_history_count(cls, value: int) -> int:
        if not 1 <= value <= 20:
            raise ValueError("CONVERSATION_CONTEXT_MESSAGES deve estar entre 1 e 20")
        return value

    @field_validator("conversation_context_characters")
    @classmethod
    def validate_history_size(cls, value: int) -> int:
        if not 100 <= value <= 16000:
            raise ValueError("CONVERSATION_CONTEXT_CHARACTERS deve estar entre 100 e 16000")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
