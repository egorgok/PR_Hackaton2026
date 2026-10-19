import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    sources_file: Path
    max_concurrent_sources: int
    max_candidates_per_source: int
    source_timeout_seconds: float
    gigachat_auth_key: str | None
    gigachat_scope: str
    gigachat_model: str
    gigachat_auth_url: str
    gigachat_api_base_url: str
    gigachat_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            sources_file=Path(os.getenv("SOURCES_FILE", ROOT / "sources.xlsx")),
            max_concurrent_sources=max(1, int(os.getenv("MAX_CONCURRENT_SOURCES", "8"))),
            max_candidates_per_source=max(1, int(os.getenv("MAX_CANDIDATES_PER_SOURCE", "40"))),
            source_timeout_seconds=max(3.0, float(os.getenv("SOURCE_TIMEOUT_SECONDS", "18"))),
            gigachat_auth_key=os.getenv("GIGACHAT_AUTH_KEY") or None,
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
        )
