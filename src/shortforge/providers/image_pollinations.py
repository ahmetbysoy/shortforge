"""Pollinations (Flux) - anahtarsiz ucretsiz gorsel uretimi.

Ucretsiz katman: anonim ~1 istek / 15 sn, gunluk tavan belirsiz; anonim
ciktida filigran olabilir. auth.pollinations.ai kaydi -> filigran kalkar,
limit yukselir. Bu asamada yalnizca erisilebilirlik kontrolu yapilir.
"""

from __future__ import annotations

from shortforge.config import Settings
from shortforge.models import HealthStatus
from shortforge.providers.base import (
    BaseProvider,
    Capability,
    Health,
    http_status_to_health,
    network_error_to_health,
)

PROBE_URL = "https://image.pollinations.ai/prompt/healthcheck?width=64&height=64&nologo=true&seed=7"


class PollinationsImageProvider(BaseProvider):
    name = "pollinations"
    capability = Capability.IMAGE
    cost_units = 0
    priority = 10
    free_tier_note = (
        "anonim: ~1 istek/15 sn, filigran olabilir | kayitli: limit yuksek, filigran yok"
    )

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        started = self._timed_start()
        headers = {}
        if self._settings.pollinations_token:
            headers["Authorization"] = f"Bearer {self._settings.pollinations_token}"
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
            ok_detail=f"HTTP {response.status_code}, {len(response.content)} bayt",
        )
        if health.status is HealthStatus.OK and not self._settings.pollinations_token:
            health.detail += " (anonim: filigran olabilir)"
        return health
