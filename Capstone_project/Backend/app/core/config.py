"""
Application configuration management.
Environment-aware settings for development, testing, and production.
"""

from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "Skeptic Engine Backend"
    APP_VERSION: str = "0.1.0"
    ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_ROOT_PATH: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    ALLOWED_HOSTS: list[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql://skeptic:skeptic_dev_password@localhost:5432/skeptic_engine"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    REDIS_EVENT_CHANNEL_PREFIX: str = "investigation_events"
    USE_REDIS_EVENTS: bool = False
    REDIS_SOCKET_TIMEOUT: float = 0.25

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    USE_CELERY: bool = False

    # EventStoreDB
    USE_EVENTSTORE: bool = False
    EVENTSTORE_URL: str = "esdb://localhost:2113?tls=false"
    EVENTSTORE_STREAM_PREFIX: str = "investigations"
    AUDIT_FALLBACK_TO_POSTGRES: bool = True

    # LLM providers
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    DEFAULT_LLM_PROVIDER: Literal["anthropic", "groq", "openai"] = "anthropic"
    ENABLE_LLM_FALLBACK: bool = True
    LLM_FALLBACK_ORDER: list[str] = ["groq", "openai"]
    LLM_REQUEST_TIMEOUT_SECONDS: float = 45.0
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL_SECONDS: int = 1800
    LLM_MAX_PROMPT_TOKENS: int = 18000
    LLM_PRICING_OVERRIDES_JSON: str = ""
    CLAUDE_MODEL_REASONING: str = "claude-3-5-sonnet-20241022"
    CLAUDE_MODEL_LIGHTWEIGHT: str = "claude-3-5-haiku-20241022"
    GROQ_MODEL_REASONING: str = "llama-3.3-70b-versatile"
    GROQ_MODEL_LIGHTWEIGHT: str = "llama-3.1-8b-instant"
    OPENAI_MODEL_REASONING: str = "gpt-4.1"
    OPENAI_MODEL_LIGHTWEIGHT: str = "gpt-4.1-mini"
    CLAUDE_MAX_TOKENS: int = 4000
    CLAUDE_TEMPERATURE: float = 0.7
    USE_REAL_AGENTS: bool = False

    # Authentication
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_REQUIRED: bool = False
    # Seed a default user on startup so the API is usable out of the box.
    SEED_DEFAULT_USER: bool = True
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = ""
    DEFAULT_ADMIN_ROLE: str = "partner"

    # Investigation defaults
    DEFAULT_MATERIALITY_THRESHOLD: float = 50000.0
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.7
    DEFAULT_ESCALATION_THRESHOLD: float = 0.5
    MAX_DEBATE_ROUNDS: int = 2
    # How many times the Supervisor may re-run a case after the Verifier rejects
    # the verdict as ungrounded, before escalating to human review.
    MAX_VERIFICATION_RETRIES: int = 1
    INVESTIGATION_TIMEOUT_MINUTES: int = 30
    ESTIMATED_AGENT_RUN_COST_USD: float = 0.21

    # Governance/UI defaults
    ENFORCE_SEGREGATION_OF_DUTIES: bool = True
    IMMUTABLE_AUDIT_LOG_REQUIRED: bool = True
    API_KEY_VAULT_NAME: str = "environment"
    UI_THEME: Literal["system", "light", "dark"] = "system"
    DISPLAY_CURRENCY: str = "USD"
    NOTIFICATIONS_ENABLED: bool = False
    AUDIT_RETENTION_YEARS: int = 7
    IP_ALLOWLIST_ENABLED: bool = False
    REQUEST_LOGGING_ENABLED: bool = True
    REQUEST_LOG_EXCLUDED_PATHS: list[str] = [
        "/health",
        "/health/detailed",
        "/docs",
        "/openapi.json",
        "/favicon.ico",
    ]

    # External APIs
    FX_API_BASE_URL: str = "https://api.frankfurter.app"
    REGISTRY_API_BASE_URL: str = ""
    EVIDENCE_VERIFICATION_PROVIDER_TIMEOUT_SECONDS: float = 3.0
    EVIDENCE_VERIFICATION_DEFAULT_TOLERANCE: float = 0.30
    EVIDENCE_VERIFICATION_FLIGHT_TOLERANCE: float = 0.25
    EVIDENCE_VERIFICATION_HOTEL_TOLERANCE: float = 0.30
    EVIDENCE_VERIFICATION_FOOD_TOLERANCE: float = 0.30
    EVIDENCE_VERIFICATION_CAB_TOLERANCE: float = 0.25
    EVIDENCE_VERIFICATION_FUEL_TOLERANCE: float = 0.10
    EVIDENCE_VERIFICATION_GST_TOLERANCE: float = 0.0
    FLIGHT_PRICE_PROVIDER_URL: str = ""
    FLIGHT_PRICE_PROVIDER_API_KEY: str = ""
    HOTEL_PRICE_PROVIDER_URL: str = ""
    HOTEL_PRICE_PROVIDER_API_KEY: str = ""
    FOOD_BENCHMARK_PROVIDER_URL: str = ""
    FOOD_BENCHMARK_PROVIDER_API_KEY: str = ""
    CAB_FARE_PROVIDER_URL: str = ""
    CAB_FARE_PROVIDER_API_KEY: str = ""
    FUEL_PRICE_PROVIDER_URL: str = ""
    FUEL_PRICE_PROVIDER_API_KEY: str = ""
    GST_VERIFICATION_PROVIDER_URL: str = ""
    GST_VERIFICATION_PROVIDER_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @field_validator(
        "CORS_ORIGINS",
        "ALLOWED_HOSTS",
        "CELERY_ACCEPT_CONTENT",
        "REQUEST_LOG_EXCLUDED_PATHS",
        "LLM_FALLBACK_ORDER",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, value):
        """Accept either a JSON list or a comma-separated string from env."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                import json

                return json.loads(stripped)
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _production_safety_checks(self):
        if self.AUTH_REQUIRED and not self.SECRET_KEY.strip():
            raise ValueError("SECRET_KEY is required when AUTH_REQUIRED=true")

        if self.USE_REAL_AGENTS:
            provider_key_env = {
                "anthropic": "ANTHROPIC_API_KEY",
                "groq": "GROQ_API_KEY",
                "openai": "OPENAI_API_KEY",
            }[self.DEFAULT_LLM_PROVIDER]
            provider_key_value = getattr(self, provider_key_env)
            if not provider_key_value.strip():
                raise ValueError(
                    f"{provider_key_env} is required when USE_REAL_AGENTS=true "
                    f"and DEFAULT_LLM_PROVIDER={self.DEFAULT_LLM_PROVIDER}"
                )

        if self.ENV != "production":
            return self

        if not self.AUTH_REQUIRED:
            raise ValueError("AUTH_REQUIRED must be true when ENV=production")
        if len(self.SECRET_KEY.strip()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters when ENV=production")
        if "*" in self.CORS_ORIGINS:
            raise ValueError("CORS_ORIGINS must be explicit when ENV=production")
        if "*" in self.ALLOWED_HOSTS:
            raise ValueError("ALLOWED_HOSTS must be explicit when ENV=production")
        if self.SEED_DEFAULT_USER and not self.DEFAULT_ADMIN_PASSWORD.strip():
            raise ValueError("DEFAULT_ADMIN_PASSWORD is required when seeding a production user")
        if self.SEED_DEFAULT_USER and len(self.DEFAULT_ADMIN_PASSWORD) < 12:
            raise ValueError("DEFAULT_ADMIN_PASSWORD must be at least 12 characters")

        return self


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
