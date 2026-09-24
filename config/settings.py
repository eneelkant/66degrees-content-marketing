from functools import lru_cache
from typing import Annotated, Any, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field("production", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    llm_provider: str = Field("mock", alias="LLM_PROVIDER")
    anthropic_api_key: str | None = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(None, alias="GEMINI_API_KEY")
    mcp_auth_token: str | None = Field(None, alias="MCP_AUTH_TOKEN")
    mcp_api_key: str | None = Field(None, alias="MCP_API_KEY")
    cors_allowed_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["*"],
        alias="CORS_ALLOWED_ORIGINS",
    )
    data_dir: str = Field("./data", alias="DATA_DIR")
    references_db_path: str = Field("./references/references.db", alias="REFERENCES_DB_PATH")
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: Any) -> list[str]:
        """Accept JSON lists, comma-separated strings, or a single origin URL."""
        if value is None or value == "":
            return ["*"]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("[") and text.endswith("]"):
                import json

                parsed = json.loads(text)
                if not isinstance(parsed, list):
                    raise ValueError(
                        "CORS_ALLOWED_ORIGINS JSON must be a list of origin strings, "
                        'e.g. ["https://chatgpt.com"].'
                    )
                return [str(item).strip() for item in parsed if str(item).strip()]
            return [part.strip() for part in text.split(",") if part.strip()]
        raise ValueError(
            "CORS_ALLOWED_ORIGINS must be a comma-separated list or JSON array of origins."
        )

    def validate_production_security(self, remote: bool = False) -> None:
        if remote and not (self.mcp_auth_token or self.mcp_api_key):
            raise ValueError(
                "Remote MCP requires MCP_AUTH_TOKEN or MCP_API_KEY in .env before starting."
            )
        if remote and "*" in self.cors_allowed_origins:
            raise ValueError(
                "Remote production MCP should not use wildcard CORS origins. "
                "Set CORS_ALLOWED_ORIGINS to explicit origins."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
