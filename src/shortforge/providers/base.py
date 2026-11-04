"""Saglayici protokolleri ve ortak yardimcilar."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from shortforge.models import HealthStatus

log = structlog.get_logger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class Capability(StrEnum):
    IMAGE = "image"
    TTS = "tts"
    MUSIC = "music"
    LLM = "llm"
    PUBLISH = "publish"


@dataclass(slots=True)
class Health:
    """Saglayici saglik raporu."""

    status: HealthStatus
    latency_ms: int | None = None
    detail: str = ""
    free_tier_note: str = ""
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return self.status in (HealthStatus.OK, HealthStatus.DEGRADED)

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "detail": self.detail,
            "free_tier_note": self.free_tier_note,
            **({"meta": self.meta} if self.meta else {}),
        }


class BaseProvider(ABC):
    """Tum saglayicilarin tabani. Alt siniflar yalnizca `health()` yazar."""

    name: str = "base"
    capability: Capability = Capability.IMAGE
    cost_units: int = 0
    priority: int = 100
    free_tier_note: str = ""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name} cap={self.capability}>"

    @abstractmethod
    async def health(self) -> Health:
        """Servisin su an kullanilabilir olup olmadigini bildirir."""

    # --- yardimcilar ---
    @staticmethod
    def _timed_start() -> float:
        return time.perf_counter()

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)

    async def _probe_http(
        self,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        """Yeniden denemeli tek HTTP probe (3 deneme, exponential + jitter)."""
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=0.4, max=3.0),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
            reraise=True,
        ):
            with attempt:
                async with httpx.AsyncClient(
                    timeout=DEFAULT_TIMEOUT, follow_redirects=True
                ) as client:
                    return await client.request(method, url, **kwargs)  # type: ignore[arg-type]
        raise RuntimeError("unreachable")  # pragma: no cover


def http_status_to_health(
    provider: str,
    status_code: int,
    *,
    latency_ms: int,
    note: str,
    ok_detail: str,
) -> Health:
    """HTTP durum kodunu saglik durumuna cevirir (ortak mantik)."""
    if 200 <= status_code < 300:
        return Health(HealthStatus.OK, latency_ms, ok_detail, note)
    if status_code in (401, 403):
        return Health(
            HealthStatus.MISSING_KEY if status_code == 401 else HealthStatus.DEGRADED,
            latency_ms,
            f"HTTP {status_code}: yetkilendirme/limit sorunu",
            note,
        )
    if status_code == 429:
        return Health(HealthStatus.DEGRADED, latency_ms, "HTTP 429: hiz limiti", note)
    if status_code >= 500:
        return Health(HealthStatus.DEGRADED, latency_ms, f"HTTP {status_code}: sunucu hatasi", note)
    return Health(HealthStatus.DOWN, latency_ms, f"HTTP {status_code}", note)


def network_error_to_health(provider: str, exc: Exception, note: str) -> Health:
    log.warning("provider.probe_failed", provider=provider, error=str(exc)[:200])
    return Health(HealthStatus.DOWN, None, f"ag hatasi: {type(exc).__name__}", note)
