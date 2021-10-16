"""Functions to parse a schedule string. In its most basic form, a schedule
will just be a Cron string. However, it may also be one of:
  - Daily
  - Weekly (on same day)
  - Monthly
  - Yearly
  - Every (day/weekday)
  - Every (X) weeks on (monday/tuesday/wednesday/...)
  - Every (X) months on the (X) day
  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
"""

from datetime import datetime
from croniter import croniter

from notion import now_utc, Task


def get_next_due_date(task: Task) -> datetime:
    """Given a task, figure out what its next due date will be based on its schedule."""
    base = now_utc()
    if task.schedule is None:
        raise Exception(f"Task {task.name} has no schedule")
    iter = croniter(task.schedule, base)
    return iter.get_next()
