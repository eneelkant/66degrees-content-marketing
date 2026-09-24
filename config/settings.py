from functools import lru_cache
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    environment: str = Field("production", alias="ENVIRONMENT")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    llm_provider: str = Field("mock", alias="LLM_PROVIDER")
    anthropic_api_key: str|None = Field(None, alias="ANTHROPIC_API_KEY")
    openai_api_key: str|None = Field(None, alias="OPENAI_API_KEY")
    gemini_api_key: str|None = Field(None, alias="GEMINI_API_KEY")
    mcp_auth_token: str|None = Field(None, alias="MCP_AUTH_TOKEN")
    mcp_api_key: str|None = Field(None, alias="MCP_API_KEY")
    cors_allowed_origins: List[str] = Field(default_factory=lambda:["*"], alias="CORS_ALLOWED_ORIGINS")
    data_dir: str = Field("./data", alias="DATA_DIR")
    references_db_path: str = Field("./data/references.db", alias="REFERENCES_DB_PATH")
    model_config=SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", populate_by_name=True, extra="ignore")
    def validate_production_security(self, remote=False):
        if remote and not (self.mcp_auth_token or self.mcp_api_key): raise ValueError("Remote MCP requires MCP_AUTH_TOKEN or MCP_API_KEY")
        if remote and "*" in self.cors_allowed_origins: raise ValueError("Remote production MCP should not use wildcard CORS origins")
@lru_cache
def get_settings(): return Settings()
