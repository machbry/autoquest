"""Freshness: how old an account's data is, against the 90-day export window."""

from datetime import date

from banking.domains.account import Freshness, FreshnessStatus

# Days since the latest export's date. The alert leaves two weeks before day 90.
WARNING_DAYS = 61
ALERT_DAYS = 76


def freshness(last_export_on: date | None, today: date) -> Freshness:
    """The freshness of data whose latest export is dated `last_export_on`."""
    if last_export_on is None:
        return Freshness(FreshnessStatus.NEVER, None)
    days = (today - last_export_on).days
    if days >= ALERT_DAYS:
        status = FreshnessStatus.ALERT
    elif days >= WARNING_DAYS:
        status = FreshnessStatus.WARNING
    else:
        status = FreshnessStatus.OK
    return Freshness(status, days)
