"""Kota defteri.

YouTube Data API kotasi *Pasifik* gece yarisinda sifirlanir; bu yuzden gun
hesabi America/Los_Angeles saat dilimine gore yapilir (PST/PDT otomatik).

Iki ayri tavan birlikte uygulanir:
  1. **Birim tavani** - API'nin gercek gunluk kotasi (YouTube icin 10.000 birim/gun).
  2. **Islem tavani** - yukleme *sayisi* (varsayilan 6/gun). Birim tavanindan
     bagimsizdir; aksi halde kapak/guncelleme cagrilari yukleme hakkini yerdi.

Kural: kredi/birim tuketen hicbir cagri `charge()` / `assert_can_afford()`
uzerinden gecmeden yapilamaz.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from shortforge.errors import QuotaExceeded
from shortforge.state import connect

PACIFIC = ZoneInfo("America/Los_Angeles")

#: Islem maliyetleri (YouTube dokumantasyonu).
UPLOAD_UNITS = 1600
THUMBNAIL_UNITS = 50
UPDATE_UNITS = 50

#: Yetenek basina gunluk *birim* tavani (None = tavan yok, sadece kayit).
DEFAULT_CAPS: dict[str, int | None] = {
    "youtube": 10_000,  # API'nin gercek gunluk birim kotasi
    "gemini": None,
    "pollinations": None,
    "pexels": None,
    "openverse": None,
}


def _as_utc(moment: datetime) -> datetime:
    """Naive datetime'i UTC kabul eder; aware olani UTC'ye cevirir.

    Mutlak sure farki icin sart: ayni tzinfo'ya sahip iki aware datetime
    arasindaki fark Python'da *duvar saati* ile hesaplanir (DST'de 1 saat
    kayar). UTC'ye cevirmek bunu engeller.
    """
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def pacific_today(now: datetime | None = None) -> date:
    """Verilen anin Pasifik saat dilimindeki gunu."""
    return _as_utc(now or datetime.now(tz=UTC)).astimezone(PACIFIC).date()


def next_reset(now: datetime | None = None) -> datetime:
    """Bir sonraki Pasifik gece yarisini (UTC olarak) dondurur."""
    local = _as_utc(now or datetime.now(tz=UTC)).astimezone(PACIFIC)
    tomorrow = local.date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=PACIFIC).astimezone(UTC)


class QuotaLedger:
    """Gunluk birim + islem tuketimini SQLite uzerinde tutan defter."""

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
        if caps:
            self._caps.update(caps)

    # --- temel ---
    def now(self) -> datetime:
        return _as_utc(self._clock())

    def today(self) -> date:
        return pacific_today(self._clock())

    def cap(self, provider: str) -> int | None:
        return self._caps.get(provider)

    def spent(self, provider: str, action: str | None = None, day: date | None = None) -> int:
        """Harcanan birim; `action` verilirse yalniz o islem turu sayilir."""
        key = (day or self.today()).isoformat()
        if action is None:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(units), 0) AS total FROM quota_usage "
                "WHERE date_pt = ? AND provider = ?",
                (key, provider),
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(units), 0) AS total FROM quota_usage "
                "WHERE date_pt = ? AND provider = ? AND action = ?",
                (key, provider, action),
            ).fetchone()
        return int(row["total"]) if row else 0

    def remaining(self, provider: str) -> int | None:
        cap = self.cap(provider)
        if cap is None:
            return None
        return max(0, cap - self.spent(provider))

    def uploads_spent(self) -> int:
        """Bugun yapilan yukleme *sayisi* (birim turevi degil, ayri sayac)."""
        return self.spent("youtube", action="upload") // UPLOAD_UNITS

    def uploads_remaining(self) -> int:
        return max(0, self._upload_daily_cap - self.uploads_spent())

    # --- yazma ---
    def assert_can_afford(self, provider: str, units: int, action: str | None = None) -> None:
        """Iki tavani birlikte denetler: birim tavani + islem tavani."""
        # Islem tavani once: "yukleme hakki bitti" mesaji "birim tavani"ndan daha eyleme donuk.
        if provider == "youtube" and action == "upload" and self.uploads_remaining() <= 0:
            raise QuotaExceeded(
                f"Bugunku yukleme hakki bitti ({self.uploads_spent()}/{self._upload_daily_cap}). "
                f"Pasifik 00:00'da yenilenir (yaklasik {self.reset_in_human()})."
            )
        units_remaining = self.remaining(provider)
        if units_remaining is not None and units > units_remaining:
            raise QuotaExceeded(
                f"'{provider}' gunluk birim tavani asildi "
                f"(kalan {units_remaining}, istenen {units}). "
                f"Pasifik 00:00'da yenilenir (yaklasik {self.reset_in_human()})."
            )

    def charge(self, provider: str, units: int, action: str = "generic") -> int:
        """Birim harcar; tavan asimi varsa QuotaExceeded firlatir.

        `action`: 'upload', 'thumbnail', 'update', 'generic' ...
        Birim turetimi yerine ayri sayac tutuldugu icin kapak/guncelleme
        cagrilari yukleme hakkini tuketmez.
        """
        if units < 0:
            raise ValueError("units negatif olamaz")
        self.assert_can_afford(provider, units, action)
        key = self.today().isoformat()
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            self._conn.execute(
                """
                INSERT INTO quota_usage (date_pt, provider, action, units) VALUES (?, ?, ?, ?)
                ON CONFLICT(date_pt, provider, action)
                DO UPDATE SET units = units + excluded.units
                """,
                (key, provider, action, units),
            )
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        return self.spent(provider)

    def reset_in_human(self, now: datetime | None = None) -> str:
        """Bir sonraki Pasifik gece yarisina kalan *mutlak* sure."""
        moment = _as_utc(now or self._clock())
        total = max(0, int((next_reset(moment) - moment).total_seconds()))
        hours, remainder = divmod(total, 3600)
        minutes = remainder // 60
        return f"{hours}s {minutes}dk"

    def reset_gap_seconds(self, now: datetime | None = None) -> int:
        """Testlerin kullandigi ham olcu: sifirlanmaya kalan saniye."""
        moment = _as_utc(now or self._clock())
        return max(0, int((next_reset(moment) - moment).total_seconds()))

    def summary(self) -> dict[str, object]:
        return {
            "date_pt": self.today().isoformat(),
            "youtube": {
                "units_spent": self.spent("youtube"),
                "units_cap": self.cap("youtube"),
                "uploads_spent": self.uploads_spent(),
                "uploads_cap": self._upload_daily_cap,
            },
            "reset_at_utc": next_reset(self.now()).isoformat(),
            "reset_in": self.reset_in_human(),
        }

    def close(self) -> None:
        self._conn.close()
