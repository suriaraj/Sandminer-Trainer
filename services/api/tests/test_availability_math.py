from datetime import UTC, datetime

from app.services.availability import overlaps


def dt(hour: int):
    return datetime(2026, 9, 23, hour, tzinfo=UTC)


def test_overlap_detected():
    assert overlaps(dt(10), dt(12), dt(11), dt(13)) is True


def test_touching_ranges_do_not_overlap():
    assert overlaps(dt(10), dt(12), dt(12), dt(14)) is False
