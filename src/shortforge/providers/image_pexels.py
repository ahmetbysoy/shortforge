"""Pexels - lisansli stok gorsel (ucretsiz API anahtari, 200 istek/saat).

Kural 3: yalnizca lisansli stok. Kullanim kaydi assets/license/manifest.json'a
yazilir (P2'de gercek uretimde).
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

PROBE_URL = "https://api.pexels.com/v1/search?query=abstract&per_page=1"


class PexelsImageProvider(BaseProvider):
    name = "pexels"
    capability = Capability.IMAGE
    cost_units = 0
    priority = 20
    free_tier_note = "ucretsiz API: 200 istek/saat, 20.000/ay | lisansli stok (atif sart degil)"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        if not self._settings.pexels_api_key:
            return Health(
                HealthStatus.MISSING_KEY,
                None,
                "PEXELS_API_KEY yok - yedek zincirde atlanir",
                self.free_tier_note,
            )
        started = self._timed_start()
        try:
            response = await self._probe_http(
                "GET", PROBE_URL, headers={"Authorization": self._settings.pexels_api_key}
            )
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
        if response.status_code == 200:
            with contextlib.suppress(ValueError):
                health.meta["photos_returned"] = len(response.json().get("photos", []))
        return health
