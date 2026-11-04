"""Saglayici secimi: fallback zinciri, override, tukenen zincir."""

from __future__ import annotations

import pytest

from shortforge.errors import NoProviderAvailable
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health
from shortforge.providers.registry import ProviderRegistry


class FakeProvider(BaseProvider):
    def __init__(
        self,
        name: str,
        capability: Capability = Capability.IMAGE,
        status: HealthStatus = HealthStatus.OK,
        priority: int = 10,
    ) -> None:
        self.name = name
        self.capability = capability
        self.priority = priority
        self._status = status
        self.calls = 0

    async def health(self) -> Health:
        self.calls += 1
        return Health(self._status, 1, f"{self.name} durumu", "test")


async def test_falls_back_to_next_provider() -> None:
    first = FakeProvider("pollinations", status=HealthStatus.DOWN, priority=10)
    second = FakeProvider("local", status=HealthStatus.OK, priority=99)
    registry = ProviderRegistry([first, second])

    provider, health = await registry.resolve(Capability.IMAGE)

    assert provider.name == "local"
    assert health.usable
    assert first.calls == 1


async def test_missing_key_is_skipped() -> None:
    skipped = FakeProvider("pexels", status=HealthStatus.MISSING_KEY, priority=10)
    usable = FakeProvider("local", status=HealthStatus.DEGRADED, priority=20)

    provider, _ = await ProviderRegistry([skipped, usable]).resolve(Capability.IMAGE)

    assert provider.name == "local"


async def test_all_down_raises_with_reasons() -> None:
    registry = ProviderRegistry(
        [
            FakeProvider("a", status=HealthStatus.DOWN),
            FakeProvider("b", status=HealthStatus.MISSING_KEY),
        ]
    )
    with pytest.raises(NoProviderAvailable) as excinfo:
        await registry.resolve(Capability.IMAGE)
    assert "a" in excinfo.value.rejected
    assert "shortforge doctor" in str(excinfo.value)


async def test_override_promotes_provider() -> None:
    preferred = FakeProvider("pexels", status=HealthStatus.OK, priority=50)
    default = FakeProvider("pollinations", status=HealthStatus.OK, priority=10)

    registry = ProviderRegistry([default, preferred], overrides={Capability.IMAGE: "pexels"})
    provider, _ = await registry.resolve(Capability.IMAGE)

    assert provider.name == "pexels"


async def test_unknown_override_is_ignored() -> None:
    only = FakeProvider("local", priority=10)
    registry = ProviderRegistry([only], overrides={Capability.IMAGE: "hayalet"})

    provider, _ = await registry.resolve(Capability.IMAGE)

    assert provider.name == "local"


async def test_health_all_survives_exploding_provider() -> None:
    class Boom(BaseProvider):
        name = "boom"
        capability = Capability.TTS

        async def health(self) -> Health:
            raise RuntimeError("patladim")

    results = await ProviderRegistry([Boom()]).health_all()

    assert results[0][1].status is HealthStatus.DOWN
