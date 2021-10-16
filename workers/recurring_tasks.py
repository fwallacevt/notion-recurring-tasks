"""Update our recurring tasks database."""

from os import environ
from typing import List
from zoneinfo import ZoneInfo

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
    for t in tasks:
        exists = Task.check_open_task_exists_by_name(client, t.name)
        if exists:
            # TODO(fwallace): logging
            # logger.debug(f"Skipping...")
            continue

        # Get the next due date, then make sure that we convert to EST so that Notion will display
        # correctly
        next_due = get_next_due_date(t)
        t.due_date = next_due.astimezone(ZoneInfo("localtime"))
        t.insert(client)


def handle_recurring_tasks():
    """Look through our todo list database to see if there are any recurring tasks
    that should be recreated."""
    client = NotionClient(api_key=environ["NOTION_API_KEY"])

    # First, get the last time this ran
    ts = Execution.get_last_execution_time_utc(client)

    # Query all tasks in our database that have been modified since that time
    tasks_to_recreate = Task.find_completed_recurring_tasks_since(client, ts)

    # Now, for each of these recurring tasks, we have to create a new task
    # for the next time that schedule should execute (unless there's an outstanding
    # task)
    create_new_recurring_tasks(client, tasks_to_recreate)

    # Save a new execution
    now = now_utc()
    execution = Execution(
        date_created=now,
        name=f"""Execution ts: {now.astimezone(ZoneInfo("localtime")).isoformat()}""",
    )
    execution.insert(client)
