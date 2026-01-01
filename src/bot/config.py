"""Configuration management module for the bot orchestration system.

This module defines the settings models and configurations for the entire system,
including database connections, bot hub settings, and provider configurations.
All settings are validated using Pydantic models.
"""

from typing import Optional

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings

from bot.bot_hub.types import (
    BotProviderType,
    ConfigProviderType,
    FunctionsProviderType,
    NodeProviderType,
    UserDataProviderType,
)
from bot.store.file_store.types import FileStoreConfig
from bot.types import (
    AgentConfig,
    PipelineConfig,
    SynthesizerConfig,
    TranscriberConfig,
    TransportConfig,
)

# Default LLM model identifiers
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_AZURE_MODEL = "gpt-4o-mini"
DEFAULT_FIREWORKS_MODEL = "accounts/fireworks/models/firefunction-v2"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class FireStoreConfig(BaseModel):
    """Configuration for Firestore bot store."""

    project_id: str = "your-gcp-project-id"
    credentials: Optional[str] = None
    credentials_path: Optional[str] = None
    database_id: str = "(default)"

    # Collection names for different data types
    nodes_collection: str = "bot_nodes"
    functions_collection: str = "bot_functions"
    configs_collection: str = "bot_configs"
    users_collection: str = "bot_users"

    # Connection settings
    timeout_seconds: int = 30


class HubConfig(BaseModel):
    """Configuration for bot hub providers."""

    bot_provider: BotProviderType = BotProviderType.LOCAL_FILE
    config_provider: ConfigProviderType = ConfigProviderType.DEFAULT_SETTINGS
    functions_provider: FunctionsProviderType = FunctionsProviderType.EMPTY
    node_provider: NodeProviderType = NodeProviderType.LOCAL_FILE
    userdata_provider: UserDataProviderType = UserDataProviderType.LOCAL_CSV
    data_base_path: str = "./data"  # Base directory for storing all provider data


class TwilioConfig(BaseModel):
    """Configuration for Twilio telephony provider."""

    account_sid: str = ""
    auth_token: str = ""
    phone_number: str = ""

    @field_validator("account_sid", "auth_token", "phone_number")
    @classmethod
    def validate_non_empty_if_set(cls, v: str, info) -> str:
        """Validate that if a value is provided, it's not just whitespace."""
        if v and not v.strip():
            raise ValueError(f"{info.field_name} cannot be only whitespace")
        return v


class PlivoConfig(BaseModel):
    """Configuration for Plivo telephony provider."""

    auth_id: str = ""
    auth_token: str = ""
    phone_number: str = ""

    @field_validator("auth_id", "auth_token", "phone_number")
    @classmethod
    def validate_non_empty_if_set(cls, v: str, info) -> str:
        """Validate that if a value is provided, it's not just whitespace."""
        if v and not v.strip():
            raise ValueError(f"{info.field_name} cannot be only whitespace")
        return v


class TelephonyConfig(BaseModel):
    """Configuration for telephony providers (Twilio & Plivo)."""

    twilio: TwilioConfig = TwilioConfig()
    plivo: PlivoConfig = PlivoConfig()


class StoreConfig(BaseModel):
    """Configuration for data storage components.

    Defines settings for database connections, Redis, file storage,
    and related connection pool parameters.
    """

    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "postgres"
    database_password: str = "postgres"
    database_name: str = "postgres"
    redis_url: str = "redis://localhost:6379"
    file_storage_config: FileStoreConfig = FileStoreConfig()
    firestore_config: FireStoreConfig = FireStoreConfig()
    # Database connection pool configuration
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_pool_timeout: int = 10
    database_pool_recycle: int = 300  # 5 minutes
    database_pool_pre_ping: bool = True

    # Database retry middleware configuration
    database_retry_enabled: bool = True
    database_retry_max_attempts: int = 3
    database_retry_delay: float = 0.5


class Settings(BaseSettings):
    """Main settings class for the application.

    Contains all configuration components including pipeline settings,
    agent settings, and various service configurations. Uses environment
    variables and defaults for initialization.
    """

    pipeline_config: PipelineConfig
    agent_config: AgentConfig
    transcriber_config: TranscriberConfig
    synthesizer_config: SynthesizerConfig
    store_config: StoreConfig
    transport_config: TransportConfig
    telephony_config: TelephonyConfig = TelephonyConfig()
    hub_config: HubConfig = HubConfig()
    workers: int = 2
    port: int = 8080
    base_url_domain: str = "localhost:8000"
    openapi_url: str = "/docs_api"
    openapi_url: str = "/docs_api"
    log_level: str = "DEBUG"
    cors_origins: list[str] = ["*"]
    host_id: str = "unknown"

    auth_username: str = "admin"
    auth_password: str = "admin"

    @property
    def database_url(self) -> str:
        """Construct async database URL from store config"""
        return (
            f"postgresql+asyncpg://{self.store_config.database_user}:"
            f"{self.store_config.database_password}@"
            f"{self.store_config.database_host}:"
            f"{self.store_config.database_port}/"
            f"{self.store_config.database_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Construct a synchronous URL for tooling that does not need asyncpg."""
        store = self.store_config
        return (
            f"postgresql://{store.database_user}:{store.database_password}@"
            f"{store.database_host}:{store.database_port}/{store.database_name}"
        )

    class Config:
        env_file = ".env"
        extra = "allow"
        env_nested_delimiter = "__"


settings = Settings()
