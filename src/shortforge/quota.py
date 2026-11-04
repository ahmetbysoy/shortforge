"""Kota defteri.

YouTube Data API kotasi *Pasifik* gece yarisinda sifirlanir; bu yuzden gun
hesabi America/Los_Angeles saat dilimine gore yapilir (PST/PDT otomatik).

Kural: kredi/birim tuketen hicbir cagri `charge()` / `assert_can_afford()`
uzerinden gecmeden yapilamaz.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from shortforge.errors import QuotaExceeded
from shortforge.state import connect

PACIFIC = ZoneInfo("America/Los_Angeles")

#: Bir yukleme cagrisinin birim maliyeti (YouTube dokumantasyonu).
UPLOAD_UNITS = 1600
THUMBNAIL_UNITS = 50
UPDATE_UNITS = 50

#: Saglayici basina gunluk birim tavani (None = tavan yok, sadece kayit).
DEFAULT_CAPS: dict[str, int | None] = {
    "youtube": None,  # upload_daily_cap * UPLOAD_UNITS ile hesaplanir
    "gemini": None,
    "pollinations": None,
    "pexels": None,
    "openverse": None,
}


def pacific_today(now: datetime | None = None) -> date:
    """Verilen anin Pasifik saat dilimindeki gunu."""
    moment = now or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(PACIFIC).date()


def next_reset(now: datetime | None = None) -> datetime:
    """Bir sonraki Pasifik gece yarisini (UTC) dondurur."""
    moment = now or datetime.now(tz=UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    local = moment.astimezone(PACIFIC)
    tomorrow = local.date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time(), tzinfo=PACIFIC).astimezone(UTC)


class QuotaLedger:
    """Gunluk birim tuketimini SQLite uzerinde tutan defter."""

    def __init__(
        self,
        db_path: Path,
        *,
        upload_daily_cap: int = 6,
        caps: dict[str, int | None] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection = connect(db_path)
        self._upload_daily_cap = upload_daily_cap
        self._clock = clock or (lambda: datetime.now(tz=UTC))
        self._caps: dict[str, int | None] = dict(DEFAULT_CAPS)
        self._caps["youtube"] = upload_daily_cap * UPLOAD_UNITS
        if caps:
            self._caps.update(caps)

    # --- temel ---
    def today(self) -> date:
        return pacific_today(self._clock())

    def cap(self, provider: str) -> int | None:
        return self._caps.get(provider)

    def spent(self, provider: str, day: date | None = None) -> int:
        key = (day or self.today()).isoformat()
        row = self._conn.execute(
            "SELECT units FROM quota_usage WHERE date_pt = ? AND provider = ?",
            (key, provider),
        ).fetchone()
        return int(row["units"]) if row else 0

    def remaining(self, provider: str) -> int | None:
        cap = self.cap(provider)
        if cap is None:
            return None
        return max(0, cap - self.spent(provider))

    def uploads_spent(self) -> int:
        return self.spent("youtube") // UPLOAD_UNITS

    def uploads_remaining(self) -> int:
        return max(0, self._upload_daily_cap - self.uploads_spent())

    # --- yazma ---
    def assert_can_afford(self, provider: str, units: int) -> None:
        remaining = self.remaining(provider)
        if remaining is not None and units > remaining:
            if provider == "youtube":
                raise QuotaExceeded(
                    "Bugunku yukleme hakki bitti "
                    f"({self.uploads_spent()}/{self._upload_daily_cap}). "
                    f"Pasifik 00:00'da yenilenir (yaklasik {self.reset_in_human()})."
                )
            raise QuotaExceeded(
                f"'{provider}' icin gunluk birim tavani asildi "
                f"(kalan {remaining}, istenen {units}). Pasifik 00:00'da yenilenir."
            )

    def charge(self, provider: str, units: int) -> int:
        """Birim harcar; tavan asimi varsa QuotaExceeded firlatir."""
        if units < 0:
            raise ValueError("units negatif olamaz")
        self.assert_can_afford(provider, units)
        key = self.today().isoformat()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                """
                INSERT INTO quota_usage (date_pt, provider, units) VALUES (?, ?, ?)
                ON CONFLICT(date_pt, provider) DO UPDATE SET units = units + excluded.units
                """,
                (key, provider, units),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        return self.spent(provider)

    def reset_in_human(self, now: datetime | None = None) -> str:
        delta = next_reset(now or self._clock()) - (now or self._clock())
        total = max(0, int(delta.total_seconds()))
        hours, remainder = divmod(total, 3600)
        minutes = remainder // 60
        return f"{hours}s {minutes}dk"

    def summary(self) -> dict[str, object]:
        return {
            "date_pt": self.today().isoformat(),
            "youtube": {
                "units_spent": self.spent("youtube"),
                "units_cap": self.cap("youtube"),
                "uploads_spent": self.uploads_spent(),
                "uploads_cap": self._upload_daily_cap,
            },
            "reset_at_utc": next_reset(self._clock()).isoformat(),
            "reset_in": self.reset_in_human(),
        }

    def close(self) -> None:
        self._conn.close()
