from __future__ import annotations

from pathlib import Path

import pytest

from shortforge.config import Settings


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    """Izole yapilandirma: .env okunmaz, tum anahtarlar bos."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        state_dir=tmp_path / "state",
        out_dir=tmp_path / "out",
        assets_dir=tmp_path / "assets",
    )


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "state" / "state.db"
