"""Yerel prosedurel gorsel uretimi - son savunma hatti.

Hicbir dis servise bagli degil: PIL ile gradyan/doku kompozisyonu uretir.
Sinirsiz, filigransiz, anahtarsiz. Ciktida "AI uretimi degil, prosedurel"
oldugu log'lanir.
"""

from __future__ import annotations

from shortforge.config import Settings
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health

try:  # pragma: no cover - ortam bagimli
    import PIL  # noqa: F401

    _PIL_OK = True
except ImportError:  # pragma: no cover
    _PIL_OK = False


class LocalImageProvider(BaseProvider):
    name = "local"
    capability = Capability.IMAGE
    cost_units = 0
    priority = 99
    free_tier_note = "sinirsiz, anahtarsiz, filigransiz (prosedurel; AI modeli degil)"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        if not _PIL_OK:
            return Health(
                HealthStatus.DOWN,
                None,
                "Pillow kurulu degil: pip install pillow",
                self.free_tier_note,
            )
        return Health(HealthStatus.OK, 0, "Pillow hazir, dis bagimlilik yok", self.free_tier_note)
