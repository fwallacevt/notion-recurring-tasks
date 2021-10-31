"""Update our recurring tasks database."""

from datetime import date, datetime
from os import environ
from typing import List, Optional, Union

from loguru import logger

from notion import Execution, NotionClient, Task
from notion.orm import now_utc
from utils.schedule import get_next_due_date


def date_if_midnight(d: datetime) -> Union[date, datetime]:
    """If the time component of the datetime is zeroed, convert to a date."""
    logger.info(f"Checking if datetime {d} has a time component...")
    if d.hour == d.minute == d.second == d.microsecond == 0:
        logger.info(f"Converting {d} to date")
        return date(d.year, d.month, d.day)
    return d


def create_new_recurring_tasks(client: NotionClient, tasks: List[Task]):
    """Create new tasks for each of the recurring tasks. Just to be extra safe, we check that
    there isn't already an uncompleted task with the same name (which could happen if our
    script gets interrupted partway through).

    For each new task we create, we'll copy everything from the old task, set the "Parent"
    to the most recently completed task (create a singly-linked list), and update the due
    date to the next occurrence of this schedule"""
    logger.info(f"Creating {len(tasks)} new recurring tasks.")
    error: Optional[Exception] = None
    for t in tasks:
        try:
            exists = Task.check_open_task_exists_by_name(client, t.name)
            if exists:
                logger.info(
                    f"There is an open task with name {t.name} - skipping"
                )
                continue

            # Get the next due date, then make sure that we convert to EST so that Notion will display
            # correctly
            # TODO(fwallace): What will local time look like if we're running on GitHub runners? How
            # do we know what local time zone is?
            next_due = get_next_due_date(t)
            # TODO(fwallace): The appropriate way to do this would actually be to generate the next due
            # date as a `date` object, rather than `datetime`, if there is no time component. That is
            # more involved and will have to come later.
            next_due = date_if_midnight(next_due)

            logger.info(
                f"Creating new task {t.name}, with new due date {next_due} (previously {t.due_date})"
            )
            t.due_date = (
                next_due.astimezone()
                if isinstance(next_due, datetime)
                else next_due
            )
            t.done = False
            t.insert(client)
        except Exception as e:
            # We catch exceptions so that if one task fails, we don't blow up the whole run.
            logger.error(f"Failed to create new task {t.name}, error: {e}")
            error = e

    if error is not None:
        # We encountered some sort of error - raise it. We don't want to fail silently
        # because that will insert a new "execution", and any failed tasks will never
        # update.
        raise error


def handle_recurring_tasks():
    """Look through our todo list database to see if there are any recurring tasks
    that should be recreated."""
    client = NotionClient(api_key=environ["NOTION_API_KEY"])

    # First, get the last time this ran
    ts = Execution.get_last_execution_time_utc(client)
    logger.info(f"Last executed: {ts}")

    # Query all tasks in our database that have been modified since that time
    tasks_to_recreate = Task.find_completed_recurring_tasks_since(client, ts)
    logger.info(
        f"Found {len(tasks_to_recreate)} recurring tasks to make: {[t.name for t in tasks_to_recreate]}"
    )

    # Now, for each of these recurring tasks, we have to create a new task
    # for the next time that schedule should execute (unless there's an outstanding
    # task)
    create_new_recurring_tasks(client, tasks_to_recreate)

    # Save a new execution
    now = now_utc()
    execution = Execution(
        date_created=now,
        name=f"""Execution ts: {now.astimezone().isoformat()}""",
    )
    logger.info(f"Creating new execution record {execution.name}")
    execution.insert(client)
