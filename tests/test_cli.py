"""doctor komutu: cikti sozlesmesi (ag cagrisi yok, sahte registry ile)."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from shortforge import cli
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health
from shortforge.providers.registry import ProviderRegistry


class FakeProvider(BaseProvider):
    name = "sahte"
    capability = Capability.IMAGE
    priority = 1
    free_tier_note = "test notu"

    async def health(self) -> Health:
        return Health(HealthStatus.OK, 5, "sorunsuz", self.free_tier_note)


def test_doctor_json_contract(monkeypatch) -> None:
    monkeypatch.setattr(
        cli, "build_default_registry", lambda *_a, **_k: ProviderRegistry([FakeProvider()])
    )
    result = CliRunner().invoke(cli.app, ["doctor", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["providers"][0]["provider"] == "sahte"
    assert payload["providers"][0]["status"] == "OK"
    assert payload["quota"]["youtube"]["uploads_cap"] == 6
    assert "python" in payload["arch"]


def test_doctor_table_renders(monkeypatch) -> None:
    monkeypatch.setattr(
        cli, "build_default_registry", lambda *_a, **_k: ProviderRegistry([FakeProvider()])
    )
    result = CliRunner().invoke(cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "KOTA" in result.output
    assert "PRIVATE" in result.output


def test_version_command() -> None:
    result = CliRunner().invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert "shortforge" in result.output
