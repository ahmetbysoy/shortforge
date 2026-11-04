"""Kota defteri: Pasifik gun gecisi (PST/PDT), tavan, atilamaz kapi."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from shortforge.errors import QuotaExceeded
from shortforge.quota import UPLOAD_UNITS, QuotaLedger, pacific_today


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
    ],
)
def test_pacific_today_handles_dst(moment: datetime, expected: date) -> None:
    assert pacific_today(moment) == expected


def test_charge_accumulates(db_path) -> None:
    ledger = QuotaLedger(db_path, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC)))
    ledger.charge("youtube", UPLOAD_UNITS)
    assert ledger.spent("youtube") == UPLOAD_UNITS
    assert ledger.uploads_spent() == 1
    assert ledger.uploads_remaining() == 5


def test_daily_cap_blocks_seventh_upload(db_path) -> None:
    ledger = QuotaLedger(
        db_path, upload_daily_cap=6, clock=FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    )
    for _ in range(6):
        ledger.assert_can_afford("youtube", UPLOAD_UNITS)
        ledger.charge("youtube", UPLOAD_UNITS)
    assert ledger.uploads_remaining() == 0
    with pytest.raises(QuotaExceeded, match="yukleme hakki bitti"):
        ledger.charge("youtube", UPLOAD_UNITS)


def test_resets_on_pacific_midnight(db_path) -> None:
    clock = FakeClock(datetime(2026, 7, 15, 12, tzinfo=UTC))
    ledger = QuotaLedger(db_path, upload_daily_cap=2, clock=clock)
    ledger.charge("youtube", UPLOAD_UNITS * 2)
    assert ledger.uploads_remaining() == 0

    # ayni UTC gunu ama Pasifik'te yeni gun (07:30Z = 00:30 PDT)
    clock.moment = datetime(2026, 7, 16, 7, 30, tzinfo=UTC)
    assert ledger.remaining("youtube") == UPLOAD_UNITS * 2
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
