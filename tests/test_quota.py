"""Kota defteri: Pasifik gun gecisi (PST/PDT), birim + islem tavanlari, DST guvenligi."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from shortforge.errors import QuotaExceeded
from shortforge.quota import UPLOAD_UNITS, QuotaLedger, next_reset, pacific_today


class FakeClock:
    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def __call__(self) -> datetime:
        return self.moment


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        # yaz (PDT, UTC-7)
        (datetime(2026, 7, 15, 6, 30, tzinfo=UTC), date(2026, 7, 14)),
        (datetime(2026, 7, 15, 7, 30, tzinfo=UTC), date(2026, 7, 15)),
        # kis (PST, UTC-8)
        (datetime(2026, 1, 15, 7, 30, tzinfo=UTC), date(2026, 1, 14)),
        (datetime(2026, 1, 15, 8, 30, tzinfo=UTC), date(2026, 1, 15)),
        # naive datetime UTC kabul edilir
        (datetime(2026, 1, 15, 8, 30), date(2026, 1, 15)),
    ],
)
def test_pacific_today_handles_dst(moment: datetime, expected: date) -> None:
    assert pacific_today(moment) == expected


@pytest.mark.parametrize(
    ("moment", "expected_seconds", "aciklama"),
    [
        # DST baslangici (2026-03-08 02:00 PST -> PDT): gece yarisina 2 saat var
        (datetime(2026, 3, 8, 6, 0, tzinfo=UTC), 2 * 3600, "DST oncesi kisa gun"),
        # 08 Mart 01:00 PST; ertesi gece yarisi PDT ile 07:00Z -> 22 saat (naif -8 ile 23 cikardi)
        (datetime(2026, 3, 8, 9, 0, tzinfo=UTC), 22 * 3600, "DST gunu: 1 saat kayma"),
        # DST bitisi (2026-11-01 02:00 PDT -> PST): gece yarisina 1 saat
        (datetime(2026, 11, 1, 6, 0, tzinfo=UTC), 1 * 3600, "DST bitisi kisa gun"),
        # 01 Kasim 01:30 PDT; ertesi gece yarisi PST ile 08:00Z -> 23.5 saat (naif -7 ile 24.5)
        (
            datetime(2026, 11, 1, 8, 30, tzinfo=UTC),
            23 * 3600 + 1800,
            "DST bitisi gunu: 1 saat kayma",
        ),
    ],
)
def test_reset_gap_is_absolute_across_dst(
    moment: datetime, expected_seconds: int, aciklama: str
) -> None:
    """Sifirlanmaya kalan sure *mutlak* olmali; duvar saati hesabi yasak.

    Ayni tzinfo'lu aware datetime farki Python'da duvar saatiyle hesaplanir ve
    DST gunlerinde 1 saat kayar. Kod UTC'ye cevirdigi icin bu testler gecer.
    """
    gap = next_reset(moment) - moment
    assert gap.total_seconds() == pytest.approx(expected_seconds), aciklama


def test_charge_accumulates_units_and_uploads(db_path) -> None:
    ledger = QuotaLedger(db_path, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC)))
    ledger.charge("youtube", UPLOAD_UNITS, "upload")

    assert ledger.spent("youtube") == UPLOAD_UNITS
    assert ledger.spent("youtube", "upload") == UPLOAD_UNITS
    assert ledger.uploads_spent() == 1
    assert ledger.uploads_remaining() == 5
    assert ledger.remaining("youtube") == 10_000 - UPLOAD_UNITS


def test_thumbnail_does_not_consume_upload_slot(db_path) -> None:
    """Kapak/guncelleme birim harcar ama yukleme hakkini yemez.

    Bu, 'yukleme sayisi = harcanan birim / 1600' turetiminin kirilgan oldugu
    noktadir: kapakli 6 yukleme 9.900 birim eder ve turetme yanlis sayardi.
    """
    ledger = QuotaLedger(
        db_path, upload_daily_cap=2, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    )
    for _ in range(2):
        ledger.charge("youtube", UPLOAD_UNITS, "upload")
        ledger.charge("youtube", 50, "thumbnail")
        ledger.charge("youtube", 50, "update")

    assert ledger.uploads_spent() == 2
    assert ledger.uploads_remaining() == 0
    assert ledger.spent("youtube") == 2 * 1700
    with pytest.raises(QuotaExceeded, match="yukleme hakki bitti"):
        ledger.charge("youtube", UPLOAD_UNITS, "upload")


def test_unit_cap_blocks_even_without_upload_cap(db_path) -> None:
    """Birim tavani (10.000) islem tavanindan bagimsiz uygulanir."""
    ledger = QuotaLedger(
        db_path, upload_daily_cap=100, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    )
    ledger.charge("youtube", 9_000, "upload")
    with pytest.raises(QuotaExceeded, match="birim tavani"):
        ledger.charge("youtube", UPLOAD_UNITS, "upload")


def test_daily_cap_blocks_seventh_upload(db_path) -> None:
    ledger = QuotaLedger(
        db_path, upload_daily_cap=6, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    )
    for _ in range(6):
        ledger.assert_can_afford("youtube", UPLOAD_UNITS, "upload")
        ledger.charge("youtube", UPLOAD_UNITS, "upload")
    assert ledger.uploads_remaining() == 0
    with pytest.raises(QuotaExceeded, match="yukleme hakki bitti"):
        ledger.charge("youtube", UPLOAD_UNITS, "upload")


def test_resets_on_pacific_midnight(db_path) -> None:
    clock = FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    ledger = QuotaLedger(db_path, upload_daily_cap=2, clock=clock)
    ledger.charge("youtube", UPLOAD_UNITS, "upload")
    ledger.charge("youtube", UPLOAD_UNITS, "upload")
    assert ledger.uploads_remaining() == 0

    # ayni UTC gunu ama Pasifik'te yeni gun (07:30Z = 00:30 PDT)
    clock.moment = datetime(2026, 7, 16, 7, 30, tzinfo=UTC)
    assert ledger.remaining("youtube") == 10_000
    assert ledger.uploads_remaining() == 2


def test_negative_units_rejected(db_path) -> None:
    ledger = QuotaLedger(db_path, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC)))
    with pytest.raises(ValueError):
        ledger.charge("youtube", -1)


def test_unlimited_provider_tracks_without_cap(db_path) -> None:
    ledger = QuotaLedger(db_path, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC)))
    assert ledger.remaining("openverse") is None
    ledger.charge("openverse", 5)
    assert ledger.spent("openverse") == 5


def test_reset_in_human_and_summary(db_path) -> None:
    ledger = QuotaLedger(db_path, clock=FakeClock(datetime(2026, 7, 15, 5, 0, tzinfo=UTC)))
    assert ledger.reset_in_human() == "2s 0dk"
    summary = ledger.summary()
    assert summary["youtube"]["uploads_cap"] == 6
    assert summary["youtube"]["units_cap"] == 10_000
    assert summary["date_pt"] == "2026-07-14"


def test_legacy_schema_is_migrated(tmp_path) -> None:
    """P0 on-surum defteri (action kolonu yok) acilista yeniden kurulur."""
    import sqlite3

    db = tmp_path / "legacy.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE quota_usage ("
        "date_pt TEXT, provider TEXT, units INTEGER, PRIMARY KEY (date_pt, provider));"
        "INSERT INTO quota_usage VALUES ('2026-07-14', 'youtube', 1600);"
    )
    conn.commit()
    conn.close()

    ledger = QuotaLedger(db, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC)))
    assert ledger.spent("youtube") == 0
    ledger.charge("youtube", UPLOAD_UNITS, "upload")
    assert ledger.uploads_spent() == 1
