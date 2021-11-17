"""Update our recurring tasks database."""

import asyncio
import time
import traceback
from datetime import date, datetime
from os import environ
from typing import Union

from loguru import logger

from notion import Execution, NotionClient, Task
from notion.orm import now_utc
from notion.timezones import Timezone
from utils.schedule import get_next_due_date


def date_if_midnight(d: datetime) -> Union[date, datetime]:
    """If the time component of the datetime is zeroed, convert to a date."""
    logger.info(f"Checking if datetime {d} has a time component...")
    if d.hour == d.minute == d.second == d.microsecond == 0:
        logger.info(f"Converting {d} to date")
        return date(d.year, d.month, d.day)
    return d


async def create_new_recurring_task(client: NotionClient, task: Task):
    """Create a new recurring task for the given task. Just to be extra safe, we check that
    there isn't already an uncompleted task with the same name (which could happen if our
    script gets interrupted partway through).

    For each new task we create, we'll copy everything from the old task, set the "Parent"
    to the most recently completed task (create a singly-linked list), and update the due
    date to the next occurrence of this schedule"""
    logger.info(f"Creating new recurring task {task.name}.")
    try:
        exists = await Task.check_open_task_exists_by_name(client, task.name)
        if exists:
            logger.info(f"There is an open task with name {task.name} - skipping")
            return

        # Get the next due date, then make sure that we convert to EST so that Notion will display
        # correctly
        # TODO(fwallace): What will local time look like if we're running on GitHub runners? How
        # do we know what local time zone is?
        next_due_datetime = get_next_due_date(task)
        # TODO(fwallace): The appropriate way to do this would actually be to generate the next due
        # date as a `date` object, rather than `datetime`, if there is no time component. That is
        # more involved and will have to come later.
        next_due = date_if_midnight(next_due_datetime)

        logger.info(
            f"Creating new task {task.name}, with new due date {next_due} (previously {task.due_date})"
        )
        task.due_date = (
            next_due.astimezone() if isinstance(next_due, datetime) else next_due
        )
        task.done = False
        await task.insert(client)
    except Exception as e:
        logger.error(
            f"Failed to recreate task {task.name}, exception {e}, traceback: {traceback.format_exc()}"
        )
        raise


async def handle_recurring_tasks():
    """Look through our todo list database to see if there are any recurring tasks
    that should be recreated."""
    client = NotionClient(api_key=environ["NOTION_API_KEY"])

    # Get the timezone the user wants to use. There may be several entries if they've changed
    # timezones, but we're only interested in the most recent (that has a name). Timezones
    # are specified as strings, as described [here](https://docs.python.org/3/library/time.html#time.tzset)
    timezone = Timezone.find_newest_by_or_raise(
        client,
        {
            "property": "Name",
            "text": {
                "is_not_empty": True,
            },
        },
    )

    # Then, use that timezone (see docs above). Since datetime and other utilities use the
    # `time` library, this will result in us using the timezone the user has requested.
    environ["TZ"] = timezone.title
    time.tzset()

    # First, get the last time this ran
    ts = await Execution.get_last_execution_time_utc(client)
    logger.info(f"Last executed: {ts}")

    # Query all tasks in our database that have been modified since that time
    tasks_to_recreate = await Task.find_completed_recurring_tasks_since(client, ts)
    logger.info(
        f"Found {len(tasks_to_recreate)} recurring tasks to make: {[t.name for t in tasks_to_recreate]}"
    )

    # Now, for each of these recurring tasks, we have to create a new task
    # for the next time that schedule should execute (unless there's an outstanding
    # task)
    logger.info(f"Creating {len(tasks_to_recreate)} new recurring tasks.")
    responses = await asyncio.gather(
        (create_new_recurring_task(client, t) for t in tasks_to_recreate),
        return_exceptions=True,
    )

    # Check if we encountered an error, and don't save the execution if we did. We don't
    # want to fail silently because that will insert a new "execution", and any failed
    # tasks will never update.
    if any(isinstance(r, Exception) for r in responses):
        raise Exception(f"Failed to create some or all tasks.")

    # Save a new execution
    now = now_utc()
    execution = Execution(
        date_created=now,
        name=f"""Execution ts: {now.astimezone().isoformat()}""",
    )
    logger.info(f"Creating new execution record {execution.name}")
    await execution.insert(client)
