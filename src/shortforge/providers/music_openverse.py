"""Openverse - CC lisansli ses/muzik arama (anahtarsiz, rate-limit'li).

Kural 3: yalnizca CC lisansli icerik. Her indirme assets/license/manifest.json'a
lisans + atif bilgisiyle kaydedilir.
"""

from __future__ import annotations

import contextlib

from shortforge.config import Settings
from shortforge.models import HealthStatus
from shortforge.providers.base import (
    BaseProvider,
    Capability,
    Health,
    http_status_to_health,
    network_error_to_health,
)

PROBE_URL = "https://api.openverse.org/v1/audio/?q=ambient&page_size=1&license=cc0"


class OpenverseMusicProvider(BaseProvider):
    name = "openverse"
    capability = Capability.MUSIC
    cost_units = 0
    priority = 10
    free_tier_note = "ucretsiz, anahtarsiz (anonim rate-limit) | yalniz CC/CC0 icerik"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        started = self._timed_start()
        headers: dict[str, str] = {"User-Agent": "shortforge/0.1 (free-tier bot)"}
        try:
            response = await self._probe_http("GET", PROBE_URL, headers=headers)
        except Exception as exc:
            return network_error_to_health(self.name, exc, self.free_tier_note)
        latency = self._elapsed_ms(started)
        health = http_status_to_health(
            self.name,
            response.status_code,
            latency_ms=latency,
            note=self.free_tier_note,
            ok_detail=f"HTTP {response.status_code}",
        )
        if health.status is HealthStatus.OK:
            with contextlib.suppress(ValueError):
                health.meta["result_count"] = response.json().get("result_count", 0)
        return health
