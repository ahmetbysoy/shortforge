"""Saglayici health() davranisi: ag taklit edilir (respx), gercek istek yok.

Kapsanan davranislar: anahtar yok, 200, 401/403, 429, 5xx, ag hatasi,
servis yok (import/binary) ve YouTube kota kapisi.
"""

from __future__ import annotations

import sys
import types
from datetime import UTC, datetime

import httpx
import pytest
import respx

from shortforge.config import Settings
from shortforge.errors import QuotaExceeded
from shortforge.models import HealthStatus
from shortforge.providers.base import (
    Health,
    http_status_to_health,
    network_error_to_health,
)
from shortforge.providers.image_local import LocalImageProvider
from shortforge.providers.image_pexels import PexelsImageProvider
from shortforge.providers.image_pollinations import PollinationsImageProvider
from shortforge.providers.llm_gemini import GeminiLLMProvider
from shortforge.providers.music_openverse import OpenverseMusicProvider
from shortforge.providers.registry import build_default_registry
from shortforge.providers.tts_edge import EdgeTTSProvider
from shortforge.providers.tts_piper import PiperTTSProvider
from shortforge.providers.youtube import YouTubeProvider
from shortforge.quota import UPLOAD_UNITS, QuotaLedger


class FakeWriter:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


# --- base.py ortak mantik ---
@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (200, HealthStatus.OK),
        (401, HealthStatus.MISSING_KEY),
        (403, HealthStatus.DEGRADED),
        (429, HealthStatus.DEGRADED),
        (500, HealthStatus.DEGRADED),
        (404, HealthStatus.DOWN),
    ],
)
def test_http_status_mapping(status_code: int, expected: HealthStatus) -> None:
    health = http_status_to_health("x", status_code, latency_ms=3, note="n", ok_detail="ok")
    assert health.status is expected
    assert health.usable is (expected in (HealthStatus.OK, HealthStatus.DEGRADED))


def test_network_error_mapping() -> None:
    health = network_error_to_health("x", httpx.ConnectError("yok"), "n")
    assert health.status is HealthStatus.DOWN
    assert health.latency_ms is None


def test_health_as_dict() -> None:
    health = Health(HealthStatus.OK, 5, "detay", "not", meta={"a": 1})
    assert health.as_dict()["meta"] == {"a": 1}
    assert Health(HealthStatus.DOWN).as_dict().get("meta") is None


# --- pollinations ---
@respx.mock
async def test_pollinations_ok(settings: Settings) -> None:
    respx.get(url__startswith="https://image.pollinations.ai/prompt/").mock(
        return_value=httpx.Response(200, content=b"png" * 10)
    )
    health = await PollinationsImageProvider(settings).health()
    assert health.status is HealthStatus.OK
    assert "anonim" in health.detail


@respx.mock
async def test_pollinations_rate_limited(settings: Settings) -> None:
    respx.get(url__startswith="https://image.pollinations.ai/prompt/").mock(
        return_value=httpx.Response(429)
    )
    health = await PollinationsImageProvider(settings).health()
    assert health.status is HealthStatus.DEGRADED


@respx.mock
async def test_pollinations_network_down(settings: Settings) -> None:
    respx.get(url__startswith="https://image.pollinations.ai/prompt/").mock(
        side_effect=httpx.ConnectError("patladim")
    )
    health = await PollinationsImageProvider(settings).health()
    assert health.status is HealthStatus.DOWN


@respx.mock
async def test_pollinations_with_token_adds_header(settings: Settings) -> None:
    cfg = settings.model_copy(update={"pollinations_token": "tok"})
    route = respx.get(url__startswith="https://image.pollinations.ai/prompt/").mock(
        return_value=httpx.Response(200, content=b"x")
    )
    health = await PollinationsImageProvider(cfg).health()
    assert health.status is HealthStatus.OK
    assert "anonim" not in health.detail
    assert route.calls[0].request.headers["authorization"] == "Bearer tok"


# --- pexels ---
async def test_pexels_without_key(settings: Settings) -> None:
    health = await PexelsImageProvider(settings).health()
    assert health.status is HealthStatus.MISSING_KEY


@respx.mock
async def test_pexels_ok_and_meta(settings: Settings) -> None:
    cfg = settings.model_copy(update={"pexels_api_key": "k"})
    respx.get(url__startswith="https://api.pexels.com/v1/search").mock(
        return_value=httpx.Response(200, json={"photos": [{"id": 1}, {"id": 2}]})
    )
    health = await PexelsImageProvider(cfg).health()
    assert health.status is HealthStatus.OK
    assert health.meta["photos_returned"] == 2


@respx.mock
async def test_pexels_invalid_json_is_tolerated(settings: Settings) -> None:
    cfg = settings.model_copy(update={"pexels_api_key": "k"})
    respx.get(url__startswith="https://api.pexels.com/v1/search").mock(
        return_value=httpx.Response(200, content=b"bozuk")
    )
    health = await PexelsImageProvider(cfg).health()
    assert health.status is HealthStatus.OK
    assert "photos_returned" not in health.meta


# --- local ---
async def test_local_always_ok(settings: Settings) -> None:
    health = await LocalImageProvider(settings).health()
    assert health.status is HealthStatus.OK
    assert health.latency_ms == 0


# --- openverse ---
@respx.mock
async def test_openverse_ok(settings: Settings) -> None:
    respx.get(url__startswith="https://api.openverse.org/v1/audio/").mock(
        return_value=httpx.Response(200, json={"result_count": 7})
    )
    health = await OpenverseMusicProvider(settings).health()
    assert health.status is HealthStatus.OK
    assert health.meta["result_count"] == 7


@respx.mock
async def test_openverse_error(settings: Settings) -> None:
    respx.get(url__startswith="https://api.openverse.org/v1/audio/").mock(
        return_value=httpx.Response(503)
    )
    health = await OpenverseMusicProvider(settings).health()
    assert health.status is HealthStatus.DEGRADED


# --- gemini ---
async def test_gemini_without_key(settings: Settings) -> None:
    assert (await GeminiLLMProvider(settings).health()).status is HealthStatus.MISSING_KEY


@respx.mock
async def test_gemini_ok(settings: Settings) -> None:
    cfg = settings.model_copy(update={"gemini_api_key": "k"})
    respx.get(url__startswith="https://generativelanguage.googleapis.com/v1beta/models").mock(
        return_value=httpx.Response(200, json={"models": [{"name": "a"}]})
    )
    health = await GeminiLLMProvider(cfg).health()
    assert health.status is HealthStatus.OK
    assert health.meta["model_count"] == 1


@respx.mock
async def test_gemini_bad_key(settings: Settings) -> None:
    cfg = settings.model_copy(update={"gemini_api_key": "k"})
    respx.get(url__startswith="https://generativelanguage.googleapis.com/v1beta/models").mock(
        return_value=httpx.Response(401)
    )
    assert (await GeminiLLMProvider(cfg).health()).status is HealthStatus.MISSING_KEY


# --- tts_edge ---
async def test_edge_tts_not_installed(settings: Settings, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "edge_tts", None)
    health = await EdgeTTSProvider(settings).health()
    assert health.status is HealthStatus.DOWN
    assert "pip install edge-tts" in health.detail


async def test_edge_tts_service_unreachable(settings: Settings, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "edge_tts", types.ModuleType("edge_tts"))

    async def boom(*_args, **_kwargs):
        raise OSError("bloklandi")

    monkeypatch.setattr("asyncio.open_connection", boom)
    health = await EdgeTTSProvider(settings).health()
    assert health.status is HealthStatus.DOWN
    assert "Piper" in health.detail


async def test_edge_tts_ok(settings: Settings, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "edge_tts", types.ModuleType("edge_tts"))
    writer = FakeWriter()

    async def fake_connect(*_args, **_kwargs):
        return object(), writer

    monkeypatch.setattr("asyncio.open_connection", fake_connect)
    health = await EdgeTTSProvider(settings).health()
    assert health.status is HealthStatus.OK
    assert "tr-TR" in health.detail
    assert writer.closed is True


# --- piper ---
async def test_piper_missing_binary(settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    assert (await PiperTTSProvider(settings).health()).status is HealthStatus.MISSING_KEY


async def test_piper_available(settings: Settings, monkeypatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/local/bin/piper")
    health = await PiperTTSProvider(settings).health()
    assert health.status is HealthStatus.OK


# --- youtube ---
async def test_youtube_missing_config_lists_keys(settings: Settings) -> None:
    health = await YouTubeProvider(settings).health()
    assert health.status is HealthStatus.MISSING_KEY
    assert "YT_CLIENT_ID" in health.detail
    assert health.meta["privacy_default"] == "private"


async def test_youtube_configured_reports_uploads_left(settings: Settings, db_path) -> None:
    cfg = settings.model_copy(
        update={"yt_client_id": "a", "yt_client_secret": "b", "yt_refresh_token": "c"}
    )
    ledger = QuotaLedger(
        db_path, upload_daily_cap=6, clock=lambda: datetime(2026, 7, 15, 12, tzinfo=UTC)
    )
    health = await YouTubeProvider(cfg, ledger).health()
    assert health.status is HealthStatus.OK
    assert health.meta["uploads_remaining_today"] == 6


async def test_youtube_preflight_blocks_when_quota_spent(settings: Settings, db_path) -> None:
    ledger = QuotaLedger(
        db_path, upload_daily_cap=1, clock=lambda: datetime(2026, 7, 15, 12, tzinfo=UTC)
    )
    provider = YouTubeProvider(settings, ledger)
    provider.preflight_upload(ledger)
    ledger.charge("youtube", UPLOAD_UNITS, "upload")

    with pytest.raises(QuotaExceeded):
        provider.preflight_upload(ledger)
    # public'e alma kapisi da denetlenir
    provider.preflight_publish(ledger)


# --- registry fabrikasi ---
def test_build_default_registry_wires_all_capabilities(settings: Settings) -> None:
    registry = build_default_registry(settings)
    names = {p.name for p in registry.all_providers()}
    assert {
        "pollinations",
        "pexels",
        "local",
        "edge_tts",
        "piper",
        "openverse",
        "gemini",
        "youtube",
    } <= names


def test_build_default_registry_respects_override(settings: Settings) -> None:
    from shortforge.providers.base import Capability

    cfg = settings.model_copy(update={"image_provider": "pexels"})
    registry = build_default_registry(cfg)
    assert [p.name for p in registry.candidates(Capability.IMAGE)] == ["pexels"]
