"""edge-tts - ucretsiz, anahtarsiz Turkce seslendirme (tr-TR).

Resmi olmayan Microsoft Edge servisi. GitHub Actions IP'lerinde bloklanma
riski vardir; bu yuzden Piper offline yedegi zorunludur (bkz. tts_piper.py).
WordBoundary olaylari kelime bazli altyazi zamanlamasi verir (ASR gerekmez).
"""

from __future__ import annotations

import asyncio

from shortforge.config import Settings
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health

EDGE_HOST = "speech.platform.bing.com"
EDGE_PORT = 443


class EdgeTTSProvider(BaseProvider):
    name = "edge_tts"
    capability = Capability.TTS
    cost_units = 0
    priority = 10
    free_tier_note = "ucretsiz, anahtarsiz, filigransiz | resmi olmayan servis (blok riski)"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def health(self) -> Health:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return Health(
                HealthStatus.DOWN,
                None,
                "edge-tts kurulu degil: pip install edge-tts (P2'de kurulur)",
                self.free_tier_note,
            )
        started = self._timed_start()
        writer = None
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(EDGE_HOST, EDGE_PORT, ssl=True), timeout=8
            )
        except (OSError, TimeoutError) as exc:
            return Health(
                HealthStatus.DOWN,
                self._elapsed_ms(started),
                f"servis erisilemedi ({type(exc).__name__}) - Piper yedegine dusulur",
                self.free_tier_note,
            )
        finally:
            if writer is not None:
                writer.close()
        latency = self._elapsed_ms(started)
        return Health(
            HealthStatus.OK,
            latency,
            f"TLS baglantisi kuruldu | ses: {self._settings.tts_voice_tr}",
            self.free_tier_note,
        )
