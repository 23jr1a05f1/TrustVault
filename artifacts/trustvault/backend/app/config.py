"""Environment-backed settings for the TrustVault API."""

import os
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    clerk_secret_key: SecretStr
    clerk_jwt_key: SecretStr | None = None
    clerk_authorized_parties: str = ""
    trustvault_admin_clerk_ids: str = ""
    database_url: SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def authorized_parties(self) -> list[str]:
        """Return explicit Clerk origins, or safe Replit-provided app domains."""
        configured = [
            item.strip()
            for item in self.clerk_authorized_parties.split(",")
            if item.strip()
        ]
        if configured:
            return configured

        domains = [
            item.strip()
            for item in os.environ.get("REPLIT_DOMAINS", "").split(",")
            if item.strip()
        ]
        dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "").strip()
        if dev_domain:
            domains.append(dev_domain)

        origins: list[str] = []
        for domain in domains:
            origin = domain if "://" in domain else f"https://{domain}"
            if origin not in origins:
                origins.append(origin)
        return origins

    @property
    def bootstrap_admin_ids(self) -> set[str]:
        """Explicit server-side Clerk IDs allowed to receive the admin role."""
        return {
            item.strip()
            for item in self.trustvault_admin_clerk_ids.split(",")
            if item.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def sqlalchemy_database_url(settings: Settings | None = None) -> str:
    """Normalize Replit's PostgreSQL URL for SQLAlchemy's psycopg driver."""
    if settings is not None:
        value = settings.database_url.get_secret_value()
    else:
        value = os.environ.get("DATABASE_URL", "")
    if not value:
        raise RuntimeError("DATABASE_URL must be configured")
    if value.startswith("postgres://"):
        value = "postgresql://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        value = value.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )
    return value
