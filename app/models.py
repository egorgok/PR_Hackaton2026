from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field, field_validator


class Platform(StrEnum):
    website = "website"
    max = "max"
    telegram = "telegram"
    vk = "vk"
    ok = "ok"
    zen = "zen"


class SearchRequest(BaseModel):
    text: str = Field(min_length=3, max_length=10_000)
    platform: list[Platform] = Field(min_length=1, max_length=20)
    editor: list[str] = Field(min_length=1, max_length=50)
    days: int = Field(default=7, ge=1, le=30)

    @field_validator("editor")
    @classmethod
    def normalize_editors(cls, values: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(value.strip() for value in values if value.strip()))
        if not cleaned:
            raise ValueError("Нужно выбрать хотя бы одну редакцию.")
        return cleaned

    @field_validator("platform")
    @classmethod
    def unique_platforms(cls, values: list[Platform]) -> list[Platform]:
        return list(dict.fromkeys(values))

    @field_validator("days")
    @classmethod
    def supported_period(cls, value: int) -> int:
        if value not in {1, 3, 7, 14, 30}:
            raise ValueError("Период должен быть одним из значений: 1, 3, 7, 14 или 30 дней.")
        return value


class FullSearchRequest(BaseModel):
    text: str = Field(min_length=3, max_length=10_000)
    platform: list[Platform] = Field(
        default_factory=lambda: list(Platform), min_length=1, max_length=20
    )
    days: int = Field(default=7, ge=1, le=30)

    @field_validator("platform")
    @classmethod
    def unique_platforms(cls, values: list[Platform]) -> list[Platform]:
        return list(dict.fromkeys(values))

    @field_validator("days")
    @classmethod
    def supported_period(cls, value: int) -> int:
        if value not in {1, 3, 7, 14, 30}:
            raise ValueError("Период должен быть одним из значений: 1, 3, 7, 14 или 30 дней.")
        return value


class Publication(BaseModel):
    editor: str
    platform: Platform
    source_name: str
    title: str
    url: str
    excerpt: str
    published_at: datetime | None = None
    date_status: str
    relevance: str
    match_method: str
    relevance_score: float | None = None
    relevance_reason: str | None = None
    matched_concepts: list[str] = Field(default_factory=list)


class SourceState(BaseModel):
    editor: str
    platform: Platform
    url: str
    status: str = "queued"
    message: str | None = None
    found: int = 0
