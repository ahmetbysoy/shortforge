"""YouTube Data API v3 - yayin saglayicisi.

Bu asamada YALNIZCA yapilandirma ve kota bilgisi raporlanir; ag cagrisi ve
OAuth akisi P4'te gelir. Kritik kurallar burada kodla sabitlenir:

* Varsayilan gizlilik daima 'private'.
* Her yukleme cagrisi once QuotaLedger.assert_can_afford ile denetlenir.
* Denetimsiz (unaudited) projede public'e cekme denemesi anlamli hata verir.
"""

from __future__ import annotations

from shortforge.config import Settings
from shortforge.errors import QuotaExceeded
from shortforge.models import HealthStatus
from shortforge.providers.base import BaseProvider, Capability, Health
from shortforge.quota import UPDATE_UNITS, UPLOAD_UNITS, QuotaLedger


class YouTubeProvider(BaseProvider):
    name = "youtube"
    capability = Capability.PUBLISH
    cost_units = UPLOAD_UNITS
    priority = 10
    free_tier_note = (
        "10.000 birim/gun | videos.insert 1600 birim ~ 6 yukleme/gun "
        "(2026-06'dan beri ayri kota kovasi iddiasi var - panelden dogrula)"
    )

    def __init__(self, settings: Settings, ledger: QuotaLedger | None = None) -> None:
        self._settings = settings
        self._ledger = ledger

    async def health(self) -> Health:
        if not self._settings.youtube_configured:
            missing = [
                key
                for key, value in {
                    "YT_CLIENT_ID": self._settings.yt_client_id,
                    "YT_CLIENT_SECRET": self._settings.yt_client_secret,
                    "YT_REFRESH_TOKEN": self._settings.yt_refresh_token,
                }.items()
                if not value
            ]
            return Health(
                HealthStatus.MISSING_KEY,
                None,
                f"eksik: {', '.join(missing)} (OAuth P4'te kurulur)",
                self.free_tier_note,
                meta={"upload_cost_units": UPLOAD_UNITS, "privacy_default": "private"},
            )
        uploads_left = self._ledger.uploads_remaining() if self._ledger else None
        return Health(
            HealthStatus.OK,
            0,
            "yapilandirma mevcut; OAuth dogrulamasi yukleme aninda yapilir",
            self.free_tier_note,
            meta={
                "upload_cost_units": UPLOAD_UNITS,
                "privacy_default": "private",
                "uploads_remaining_today": uploads_left,
            },
        )

    def preflight_upload(self, ledger: QuotaLedger) -> None:
        """Yukleme oncesi kota kapisi - atlanamaz."""
        ledger.assert_can_afford(self.name, UPLOAD_UNITS, "upload")

    def preflight_publish(self, ledger: QuotaLedger) -> None:
        """Public'e alma oncesi kota kapisi."""
        ledger.assert_can_afford(self.name, UPDATE_UNITS, "update")


__all__ = ["QuotaExceeded", "YouTubeProvider"]
