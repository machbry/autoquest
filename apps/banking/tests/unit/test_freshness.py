from datetime import date, timedelta

import pytest

from banking.domains.account import Freshness, FreshnessStatus
from banking.services.accounts.freshness import freshness

TODAY = date(2026, 11, 1)


def test_account_never_imported():
    assert freshness(None, TODAY) == Freshness(FreshnessStatus.NEVER, None)


@pytest.mark.parametrize(
    ("days", "status"),
    [
        (0, FreshnessStatus.OK),
        (60, FreshnessStatus.OK),
        (61, FreshnessStatus.WARNING),
        (75, FreshnessStatus.WARNING),
        (76, FreshnessStatus.ALERT),
        (120, FreshnessStatus.ALERT),
    ],
)
def test_status_follows_days_since_the_latest_export(days, status):
    assert freshness(TODAY - timedelta(days=days), TODAY) == Freshness(status, days)
