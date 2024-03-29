# Notion extensions

![Tests](https://github.com/fwallacevt/notion-recurring-tasks/actions/workflows/ci.yml/badge.svg)
![Recurring tasks](https://github.com/fwallacevt/notion-recurring-tasks/actions/workflows/run-recurring-tasks.yml/badge.svg)

This project aims to extend [Notion's](https://www.notion.so/product) functionality to work more broadly for a variety
of users and provide a skeleton for other developers to create well-formulated extensions using [Notion's
API](https://developers.notion.com/).

- [Description](#description)
- [Features](#features)
  - [Recurring tasks for todo lists](#recurring-tasks-for-todo-lists)
  - [Habit tracking](#habit-tracking)
  - [Interfacing with Google Calendar](#interfacing-with-google-calendar)
  - [Dashboard generation](#dashboard-generation)

## Description

Inspired by personal need and the [lack of support for advanced to-do list
functionality](https://www.reddit.com/r/Notion/comments/o1i2ge/come_on_notion_we_need_recurring_tasks_in_2021/) in
Notion, I decided to build a rough version of the functionality I wanted using Notion's API.

Initially, I implemented this using Notion's Javascript SDK. However, the json was clunky to work with, and the lack of
typing made it difficult to develop on top of the API. To resolve this, I opted to switch to Python, using
[mypy](https://github.com/python/mypy) for [static
typechecking](https://en.wikipedia.org/wiki/Type_system#Static_type_checking), and create an
[ORM](https://en.wikipedia.org/wiki/Object%E2%80%93relational_mapping) wrapper around Notion databases. This has several
advantages:

- Static type checking helps catch many bugs before they are deployed, increasing overall code quality (and readability)
- ORM layer provides a clean, typed, programmatic interface to Notion's API
- ORM generator means that we can easily handle database changes or interfacing with new databases, increasing
  development velocity dramatically
- ORM layer can be extended to support other Notion data types, or even other Notion objects (e.g. pages). This will
  make it simple to develop clean extensions for most use cases

Different extensions are run using [GitHub actions](https://github.com/features/actions) for simplicity. Secrets can
easily [be
stored](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository)
to be passed to actions, and schedules or triggers can be customized. For an example of setting up actions, see below.

This project's primary value is as an example for others to use when developing against Notion's API.

## Basic usage

- [How to develop](./docs/developing.md)
- [How to use the ORM wrapper](./docs/orm-usage.md)
- [Customize schedules or triggers](./docs/customizing-schedules.md)

The core value of this project is its wrapper around Notion databases (which can be extended to generic pages). Once
you've [generated the Python wrapper for your database](./docs/orm-usage.md#generating-or-updating-orm-classes), you can
[query Notion incredibly easily](./docs/orm-usage.md#programmatic-usage).

## Features

The following features are supported by this project.

### Recurring tasks for todo lists

This extension adds support for recurring tasks to Notion to do lists. It requires two tables to function, one
containing tasks, and the other containing timestamps of its executions. The latter is used to limit query sizes by only
looking at tasks modified since the last execution.

This extension supports Cron string schedules, as well as the following forms:

- Every (X) (days|weeks|months|years)
- Every (X) (days|weeks|months|years), at (9am)
- Every (X) (days|weeks|months|years), from (due date/completed date)
- Every (X) (days|weeks|months|years), from (due date/completed date), at (9am)
- Every (X) (days|weeks|months|years), at (9am), from (due date/completed date)
- Every (X) weeks, on (mon/tue/wed, etc.)
- Every (X) weeks, on (mon/tue/wed, etc.), at (9am)
- Every (X) months, on the last day
- Every (X) months, on the last day, at (9am)
- Every (X) (weeks|months|years), on day (1/3/5-7)
- Every (X) (weeks|months|years), on day (1/3/5-7), at (9am)
- Every (X) (weeks|months|years), at (9am), on day (X)
- Every (day|weekday)
- Every (day|weekday), at (9am)
- Every (mon/tue/wed, etc.)
- Every (mon/tue/wed, etc.), at (9am)

where values in parentheses are specified by the user.

The syntax in these strings is extremely important. Our parser expects that each part of the schedule be separated by a
comma, and that consecutive elements of lists be separated by forward slashes (/). Some examples of valid strings are:

- "Every mon/tuesday, at 9am" (equivalent to "Every 1 weeks, on day 1/2, at 9am")
- "Every 1 months, on day 1/5-9" ("5-9" will be interpreted as a range, meaning the schedule should execute on days 1,
  5, 6, 7, 8, and 9)
- "Every 1 months, on day 1"
- "Every 1 months, on the last day"

To specify days of the week, you may use either abbreviations (e.g. mon, tue) or the full day name (monday, tuesday).
Time (9am) must be in dateutil-compatible string format.

If "from (due date/completed date)" is not specified, we will choose a default, depending on the configuration. Note
that you cannot specify _*both*_ "start from" _*and*_ specific days to execute on.

#### Setup

First, clone the [provided todo list
template](https://airy-gravity-ede.notion.site/Todo-List-Template-5209eba6a8754039b7cd316cbb2f1e21). You
may also use your own databases, with the following requirements:

- The database you store your tasks in must have:
  - name (title)
  - last_edited_time (datetime)
  - done (checkbox)
  - status (select; with option "to do")
  - due date (datetime)
  - schedule (str)
- The database you store executions in must have:
  - name (title)
  - date_created (datetime)
- The database you store timezone information in must have:
  - name (title), containing at least one entry with a [correctly formatted](https://docs.python.org/3/library/time.html#time.tzset) timezone string

_*If you create your own databases, you will need to [regenerate ORM classes](./docs/orm-usage.md).*_

Once your databases are created, [create an
integration](https://developers.notion.com/docs/getting-started#step-1-create-an-integration) and [give it access to
both databases](https://developers.notion.com/docs/getting-started#step-2-share-a-database-with-your-integration). Next,
[fork this repository](https://docs.github.com/en/get-started/quickstart/fork-a-repo#forking-a-repository). Finally,
create the following [repository
secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository)
on your fork:

- NOTION_TASKS_DB_ID (your tasks database ID; see [here](https://stackoverflow.com/a/67729240) for how to get a database
  ID)
- NOTION_EXECUTIONS_DB_ID (your executions database ID)
- NOTOIN_TIMEZONE_DB_ID (your timezone database ID)
- NOTION_API_KEY (your integration token; if you didn't copy it earlier, you may copy it by going to "Settings &
  Members" -> "Integrations", clicking the ellipsis next to your api key, and selecting "Copy internal integration
  token")

And just like that, you should be good to go! Now, you can [customize your databases](./docs/orm-usage.md) or [the
extension's schedule](./customizing-schedules.md).

### Habit tracking

To be implemented.

### Interfacing with Google Calendar

To be implemented.

### Dashboard generation

To be implemented.
