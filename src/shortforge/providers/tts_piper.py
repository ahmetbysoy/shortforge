"""Piper - offline, MIT lisansli, tamamen ucretsiz TTS (edge-tts yedegi)."""

from __future__ import annotations

import shutil

from shortforge.config import Settings
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health


class PiperTTSProvider(BaseProvider):
    name = "piper"
    capability = Capability.TTS
    cost_units = 0
    priority = 50
    free_tier_note = "MIT, offline, sinirsiz | ses modeli indirilirse calisir"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        binary = shutil.which("piper")
        if not binary:
            return Health(
                HealthStatus.MISSING_KEY,
                None,
                "piper binary yok (pip install piper-tts + tr_TR modeli)",
                self.free_tier_note,
            )
        return Health(HealthStatus.OK, 0, f"binary: {binary}", self.free_tier_note)
