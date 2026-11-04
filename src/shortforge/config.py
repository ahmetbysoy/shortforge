"""Yapilandirma: pydantic-settings, env + .env, eksik anahtar uygulamayi cokertmez."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Sir olarak kabul edilen alanlar (log maskeleme + raporlarda kullanilir).
SECRET_FIELDS: tuple[str, ...] = (
    "yt_client_secret",
    "yt_refresh_token",
    "gemini_api_key",
    "groq_api_key",
    "pexels_api_key",
    "pollinations_token",
    "openverse_client_secret",
)


class Settings(BaseSettings):
    """Tum calisma zamani yapilandirmasi. Env adi = alan adi (buyuk harf)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- calisma modu ---
    env: str = "dev"
    log_level: str = "INFO"
    dry_run: bool = True
    daily_video_limit: int = Field(default=1, ge=1, le=6)

    # --- YouTube ---
    yt_client_id: str | None = None
    yt_client_secret: str | None = None
    yt_refresh_token: str | None = None
    yt_daily_upload_cap: int = Field(default=6, ge=1, le=100)

    # --- LLM ---
    gemini_api_key: str | None = None
    groq_api_key: str | None = None

    # --- gorsel ---
    pexels_api_key: str | None = None
    pollinations_token: str | None = None

    # --- muzik ---
    openverse_client_id: str | None = None
    openverse_client_secret: str | None = None

    # --- seslendirme ---
    tts_voice_tr: str = "tr-TR-AhmetNeural"

    # --- saglayici override (bos = otomatik secim) ---
    image_provider: str | None = None
    tts_provider: str | None = None
    llm_provider: str | None = None
    music_provider: str | None = None

    # --- yollar ---
    state_dir: Path = Path("state")
    out_dir: Path = Path("out")
    assets_dir: Path = Path("assets")

    @property
    def secret_values(self) -> list[str]:
        return [getattr(self, name) for name in SECRET_FIELDS if getattr(self, name)]

    @property
    def youtube_configured(self) -> bool:
        return bool(self.yt_client_id and self.yt_client_secret and self.yt_refresh_token)

    @property
    def db_path(self) -> Path:
        return self.state_dir / "state.db"

    def ensure_dirs(self) -> None:
        for path in (self.state_dir, self.out_dir):
            path.mkdir(parents=True, exist_ok=True)

    def provider_override(self, capability: str) -> str | None:
        """Yetenek adina gore env override degerini dondurur."""
        return {
            "image": self.image_provider,
            "tts": self.tts_provider,
            "llm": self.llm_provider,
            "music": self.music_provider,
            "publish": None,
        }.get(capability)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    """Testlerde .env degisimini izole etmek icin."""
    get_settings.cache_clear()
