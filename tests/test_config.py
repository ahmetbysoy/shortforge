"""Yapilandirma: eksik anahtar cokertmez, override calisir, sinirlar uygulanir."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from shortforge.config import Settings


def test_missing_youtube_keys_do_not_crash(settings: Settings) -> None:
    assert settings.youtube_configured is False
    assert settings.secret_values == []


def test_youtube_configured_when_all_present() -> None:
    cfg = Settings(
        _env_file=None,  # type: ignore[call-arg]
        yt_client_id="a",
        yt_client_secret="b",
        yt_refresh_token="c",
    )
    assert cfg.youtube_configured is True
    assert len(cfg.secret_values) == 2  # client_id sir degil


def test_daily_video_limit_bounds() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, daily_video_limit=9)  # type: ignore[call-arg]


def test_provider_override_lookup(settings: Settings) -> None:
    cfg = settings.model_copy(update={"image_provider": "pexels"})
    assert cfg.provider_override("image") == "pexels"
    assert cfg.provider_override("tts") is None


def test_ensure_dirs_creates_paths(settings: Settings) -> None:
    settings.ensure_dirs()
    assert isinstance(settings.state_dir, Path) and settings.state_dir.is_dir()
    assert settings.out_dir.is_dir()


def test_defaults_are_safe(settings: Settings) -> None:
    assert settings.dry_run is True
    assert settings.yt_daily_upload_cap == 6
