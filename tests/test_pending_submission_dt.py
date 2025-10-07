from datetime import datetime

from bot.config import CFG
from bot.main import _pending_submission_dt


def _dt(year, month, day, hour=0, minute=0, second=0):
    return datetime(year, month, day, hour, minute, second, tzinfo=CFG.tz_moscow)


def test_pending_submission_dt_prefers_iso():
    original = _dt(2025, 10, 6, 23, 50)
    result = _pending_submission_dt({"dt_iso": original.isoformat()})
    assert result == original


def test_pending_submission_dt_falls_back_to_day_key():
    original = _dt(2025, 10, 6, 8, 30)
    result = _pending_submission_dt({"day": original.strftime("%Y-%m-%d")})
    assert result.date() == original.date()
    assert result.tzinfo == CFG.tz_moscow
