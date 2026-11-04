"""Gemini API - ucretsiz katman senaryo uretimi (kart gerekmez).

Not: ucretsiz katmanda gonderilen icerik urun gelistirmede kullanilabilir;
ticari/gizli veri gonderme. Anahtar yoksa saglayici atlanir (Groq yedegi).
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

PROBE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMProvider(BaseProvider):
    name = "gemini"
    capability = Capability.LLM
    cost_units = 0
    priority = 10
    free_tier_note = "ucretsiz katman (gunluk istek limiti) | veri urun gelistirmede kullanilabilir"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        if not self._settings.gemini_api_key:
            return Health(
                HealthStatus.MISSING_KEY,
                None,
                "GEMINI_API_KEY yok - Groq yedegine dusulur",
                self.free_tier_note,
            )
        started = self._timed_start()
        try:
            response = await self._probe_http(
                "GET", PROBE_URL, params={"key": self._settings.gemini_api_key}
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
                health.meta["model_count"] = len(response.json().get("models", []))
        return health
