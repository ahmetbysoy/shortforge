"""Saglayici secimi: yetenek -> oncelik sirali adaylar, health ile runtime karar.

Kural 2 (tek araciya bagimli olma) burada uygulanir: hicbir is modulu somut
sinifi import etmez; yalnizca resolve() cagirir.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable, Sequence

import structlog

from shortforge.config import Settings
from shortforge.errors import NoProviderAvailable
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health
from shortforge.quota import UPLOAD_UNITS, QuotaLedger

log = structlog.get_logger(__name__)

CAPABILITY_LABELS: dict[Capability, str] = {
    Capability.IMAGE: "gorsel",
    Capability.TTS: "seslendirme",
    Capability.MUSIC: "muzik",
    Capability.LLM: "senaryo",
    Capability.PUBLISH: "yayin",
}


class ProviderRegistry:
    """Yetenek basina sirali saglayici listesi tutar."""

    def __init__(
        self,
        providers: Iterable[BaseProvider],
        *,
        overrides: dict[Capability, str] | None = None,
    ) -> None:
        self._by_capability: dict[Capability, list[BaseProvider]] = {}
        for provider in providers:
            self._by_capability.setdefault(provider.capability, []).append(provider)
        for bucket in self._by_capability.values():
            bucket.sort(key=lambda p: p.priority)
        self._overrides = overrides or {}

    def all_providers(self) -> Sequence[BaseProvider]:
        return [p for bucket in self._by_capability.values() for p in bucket]

    def candidates(self, capability: Capability) -> list[BaseProvider]:
        """Override verildiyse o saglayici basa alinir (elenmez, ilk denenir)."""
        bucket = list(self._by_capability.get(capability, []))
        override = self._overrides.get(capability)
        if override:
            matching = [p for p in bucket if p.name == override]
            if not matching:
                log.warning(
                    "registry.override_unknown",
                    capability=capability.value,
                    override=override,
                    available=[p.name for p in bucket],
                )
            else:
                bucket = matching + [p for p in bucket if p.name != override]
        return bucket

    async def health_all(self) -> list[tuple[BaseProvider, Health]]:
        providers = self.all_providers()
        results = await asyncio.gather(*(p.health() for p in providers), return_exceptions=True)
        output: list[tuple[BaseProvider, Health]] = []
        for provider, result in zip(providers, results, strict=True):
            if isinstance(result, BaseException):
                output.append(
                    (
                        provider,
                        Health(HealthStatus.DOWN, None, f"health() hata: {type(result).__name__}"),
                    )
                )
            else:
                output.append((provider, result))
        return output

    async def resolve(self, capability: Capability) -> tuple[BaseProvider, Health]:
        """Kullanilabilir ilk saglayiciyi dondurur; hicbiri yoksa NoProviderAvailable."""
        candidates = self.candidates(capability)
        rejected: dict[str, str] = {}
        for provider in candidates:
            health = await provider.health()
            if health.usable:
                log.info(
                    "registry.chosen",
                    capability=capability.value,
                    chosen=provider.name,
                    status=health.status.value,
                    rejected=rejected,
                )
                return provider, health
            rejected[provider.name] = f"{health.status.value}: {health.detail}"
        raise NoProviderAvailable(capability.value, rejected)


def build_default_registry(
    settings: Settings, ledger: QuotaLedger | None = None
) -> ProviderRegistry:
    """Tum yerlesik saglayicilari yapilandirmayla birlikte kurar."""
    from shortforge.providers.image_local import LocalImageProvider
    from shortforge.providers.image_pexels import PexelsImageProvider
    from shortforge.providers.image_pollinations import PollinationsImageProvider
    from shortforge.providers.llm_gemini import GeminiLLMProvider
    from shortforge.providers.music_openverse import OpenverseMusicProvider
    from shortforge.providers.tts_edge import EdgeTTSProvider
    from shortforge.providers.tts_piper import PiperTTSProvider
    from shortforge.providers.youtube import YouTubeProvider

    providers: list[BaseProvider] = [
        PollinationsImageProvider(settings),
        PexelsImageProvider(settings),
        LocalImageProvider(settings),
        EdgeTTSProvider(settings),
        PiperTTSProvider(settings),
        OpenverseMusicProvider(settings),
        GeminiLLMProvider(settings),
        YouTubeProvider(settings, ledger),
    ]
    overrides = {
        capability: name
        for capability in Capability
        if (name := settings.provider_override(capability.value))
    }
    return ProviderRegistry(providers, overrides=overrides)


__all__ = ["CAPABILITY_LABELS", "UPLOAD_UNITS", "ProviderRegistry", "build_default_registry"]
