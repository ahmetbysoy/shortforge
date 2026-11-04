"""Veri modeli: tek dogruluk kaynagi (pydantic).

LLM ciktisi bu semaya zorlanir; parse edilemezse yeniden denenir.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Motion = Literal["zoom_in", "zoom_out", "pan_left", "pan_right", "static"]


class JobStatus(StrEnum):
    DRAFT = "draft"
    RENDERED = "rendered"
    UPLOADED = "uploaded"
    APPROVED = "approved"
    PUBLISHED = "published"


class Scene(BaseModel):
    """Tek bir sahne: anlati metni + gorsel istemi + hareket."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1, le=7)
    narration: str = Field(min_length=1, max_length=400)
    image_prompt: str = Field(min_length=3, max_length=500)
    motion: Motion = "zoom_in"
    duration_hint: float | None = Field(default=None, ge=1.0, le=20.0)
    source_note: str | None = Field(default=None, max_length=200)


class Script(BaseModel):
    """Video senaryosu: hook + 3-7 sahne + CTA + hashtag + kaynaklar."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=3, max_length=120)
    hook: str = Field(min_length=5, max_length=90, description="Ilk 3 saniye kancasi")
    scenes: list[Scene] = Field(min_length=3, max_length=7)
    cta: str = Field(default="", max_length=120)
    hashtags: list[str] = Field(min_length=3, max_length=5)
    sources: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("hashtags")
    @classmethod
    def _normalize_hashtags(cls, values: list[str]) -> list[str]:
        normalized = []
        for tag in values:
            tag = tag.strip().lstrip("#")
            if not tag:
                raise ValueError("bos hashtag olamaz")
            normalized.append(f"#{tag}")
        return normalized

    @model_validator(mode="after")
    def _collect_warnings(self) -> Script:
        if not self.sources:
            self.warnings.append(
                "sources bos: bilgi iddialari icin kaynak eklenmeli (YouTube politikasi)"
            )
        if len(self.hook) > 70:
            self.warnings.append("hook uzun: mobil onizlemede kesilebilir")
        return self

    @property
    def estimated_duration_s(self) -> float:
        """Kaba sure tahmini: Turkce ~2.6 kelime/saniye."""
        words = len(self.hook.split()) + sum(len(s.narration.split()) for s in self.scenes)
        return round(words / 2.6, 1)


class VideoJob(BaseModel):
    """Uretim/yayin isi. Varsayilan gizlilik daima 'private'."""

    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    script: Script
    privacy: Literal["private", "public"] = "private"
    status: JobStatus = JobStatus.DRAFT
    audio_path: str | None = None
    ass_path: str | None = None
    mp4_path: str | None = None
    thumbnail_path: str | None = None
    youtube_video_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    def mark(self, status: JobStatus) -> VideoJob:
        """Durum gecislerini kisitlar: public'e cikis yalnizca approved sonrasi."""
        allowed: dict[JobStatus, set[JobStatus]] = {
            JobStatus.DRAFT: {JobStatus.RENDERED},
            JobStatus.RENDERED: {JobStatus.UPLOADED},
            JobStatus.UPLOADED: {JobStatus.APPROVED},
            JobStatus.APPROVED: {JobStatus.PUBLISHED},
            JobStatus.PUBLISHED: set(),
        }
        if status not in allowed[self.status]:
            raise ValueError(f"gecersiz durum gecisi: {self.status} -> {status}")
        self.status = status
        return self


class HealthStatus(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"
    MISSING_KEY = "MISSING_KEY"
