import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    sources_file: Path
    jobs_db_file: Path
    cookie_secure: bool
    cookie_samesite: str
    cookie_max_age_seconds: int
    cors_origins: tuple[str, ...]
    max_concurrent_sources: int
    max_candidates_per_source: int
    source_timeout_seconds: float
    gigachat_auth_key: str | None
    gigachat_ca_bundle_file: Path | None
    gigachat_scope: str
    gigachat_model: str
    gigachat_auth_url: str
    gigachat_api_base_url: str
    gigachat_timeout_seconds: float
    ai_api_key: str | None
    ai_model: str
    ai_base_url: str
    ai_timeout_seconds: float
    vk_token: str | None

    def __post_init__(self) -> None:
        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE должен быть lax, strict или none.")
        if self.cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("COOKIE_SAMESITE=none требует COOKIE_SECURE=true.")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            sources_file=Path(os.getenv("SOURCES_FILE", ROOT / "sources.xlsx")),
            jobs_db_file=Path(os.getenv("JOBS_DB_FILE", ROOT / "data" / "jobs.sqlite3")),
            cookie_secure=os.getenv("COOKIE_SECURE", "false").casefold() == "true",
            cookie_samesite=os.getenv("COOKIE_SAMESITE", "lax").casefold(),
            cookie_max_age_seconds=max(
                3600, int(os.getenv("COOKIE_MAX_AGE_SECONDS", str(365 * 24 * 60 * 60)))
            ),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv(
                    "CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173",
                ).split(",")
                if origin.strip()
            ),
            max_concurrent_sources=max(1, int(os.getenv("MAX_CONCURRENT_SOURCES", "8"))),
            max_candidates_per_source=max(1, int(os.getenv("MAX_CANDIDATES_PER_SOURCE", "40"))),
            source_timeout_seconds=max(3.0, float(os.getenv("SOURCE_TIMEOUT_SECONDS", "18"))),
            gigachat_auth_key=os.getenv("GIGACHAT_AUTH_KEY") or None,
            gigachat_ca_bundle_file=(
                Path(os.getenv("GIGACHAT_CA_BUNDLE_FILE"))
                if os.getenv("GIGACHAT_CA_BUNDLE_FILE")
                else (
                    ROOT / "certs" / "russian_trusted_root_ca_pem.crt"
                    if (ROOT / "certs" / "russian_trusted_root_ca_pem.crt").is_file()
                    else None
                )
            ),
            gigachat_scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
            gigachat_model=os.getenv("GIGACHAT_MODEL", "GigaChat"),
            gigachat_auth_url=os.getenv(
                "GIGACHAT_AUTH_URL",
                "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
            ),
            gigachat_api_base_url=os.getenv(
                "GIGACHAT_API_BASE_URL",
                "https://gigachat.devices.sberbank.ru/api/v1",
            ).rstrip("/"),
            gigachat_timeout_seconds=max(3.0, float(os.getenv("GIGACHAT_TIMEOUT_SECONDS", "22"))),
            ai_api_key=os.getenv("AI_API_KEY") or None,
            ai_model=os.getenv("AI_MODEL", "gpt-6.1-sol"),
            ai_base_url=os.getenv("AI_BASE_URL", "https://darkapi.shop/v1").rstrip("/"),
            ai_timeout_seconds=max(3.0, float(os.getenv("AI_TIMEOUT_SECONDS", "22"))),
            vk_token=os.getenv("VK_TOKEN") or None,
        )
