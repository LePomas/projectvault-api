from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ProjectVault API"
    app_env: str = "local"
    cors_allowed_origins: str = ""
    public_registration_enabled: bool = True

    database_url: str
    jwt_secret_key: str = "change-this-local-secret-with-32-bytes-minimum"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    project_storage_limit_bytes: int = 104_857_600
    document_storage_backend: str = "local"
    document_storage_path: str = "storage/documents"
    s3_endpoint_url: str | None = None
    s3_public_endpoint_url: str | None = None
    s3_bucket: str = "projectvault-documents"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    s3_presigned_url_expires_seconds: int = 900

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
