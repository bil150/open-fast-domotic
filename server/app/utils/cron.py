from datetime import datetime

from croniter import croniter


def is_valid_cron(expression: str) -> bool:
    """Standard 5-field cron (croniter would also accept a 6th "seconds" field)."""
    return len(expression.split()) == 5 and croniter.is_valid(expression)


def matches(expression: str, moment: datetime) -> bool:
    return is_valid_cron(expression) and croniter.match(expression, moment)


def next_run(expression: str, base: datetime | None = None) -> str | None:
    if not is_valid_cron(expression):
        return None
    following: datetime = croniter(expression, base or datetime.now()).get_next(datetime)
    return following.isoformat(timespec="minutes")
