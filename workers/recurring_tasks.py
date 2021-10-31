"""Update our recurring tasks database."""

from os import environ
from typing import List, Optional
from zoneinfo import ZoneInfo

from loguru import logger

from notion import Execution, NotionClient, Task
from notion.orm import now_utc
from utils.schedule import get_next_due_date


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
            # TODO(fwallace): When I'm formatting the due date, I should remove the time
            # component if it's all zeroes (actually requires changes to ORM)
            # TODO(fwallace): Confirm that this will confirm a due date _in local time_ (make sure that
            # timestamps on the objects are parsed as UTC or local time, consistently)
            # TODO(fwallace): Confirm that this will set the due date in notion _in local time_ (make sure
            # that due dates are set as local time)
            # TODO(fwallace): What will local time look like if we're running on GitHub runners? How
            # do we know what local time zone is?
            next_due = get_next_due_date(t)

            logger.info(
                f"Creating new task {t.name}, with new due date {next_due} (previously {t.due_date})"
            )
            t.due_date = next_due.astimezone()
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
    logger.info(f"Found {len(tasks_to_recreate)} recurring tasks to make...")

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
