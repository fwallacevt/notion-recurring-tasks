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
template](https://airy-gravity-ede.notion.site/1fdbd589f8764f08bef994417a4452b4?v=20895c9c302e4bdaa6ebee836c2d2ab1). You
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
- NOTION_API_KEY (your integration token; if you didn't copy it earlier, you may copy it by going to "Settings &
  Members" -> "Integrations", clicking the ellipsis next to your api key, and selecting "Copy internal integration
  token")

And just like that, you should be good to go! Now, you can [customize your databases](./docs/orm-usage.md) or [the
extension's schedule](./customizing-schedules.md).

### Habit tracking

Coming soon!

### Interfacing with Google Calendar

Coming soon!

### Dashboard generation

Coming soon!

## TODOs

- [x] Add comments/doc strings
- [x] Use Notion DB for keeping track of runs, not a file
- [x] Add gh action to run nightly (date might get messed up because Notion API only compares dates)
- [x] Improve copy functionality (should be able to take arbitrary database and property names, fetch the types, and know
      how to copy from one to the other; e.g. we know how to copy multi-select, select, date, etc.)
- [x] Add gh action to run python job 2x/day
- [x] Remove/archive JS code
- [x] Improve Cron functionality - cron, or:
  - Daily
  - Weekly (on same day)
  - Monthly
  - Yearly
  - Every (day/weekday)
  - Every (X) weeks on (monday/tuesday/wednesday/...)
  - Every (X) months on the (X) day
  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
- [x] Add tests
  - [x] Test schedule utility
- [x] Make schedule attributes read only
- [x] Run tests on PRs
- [x] Lots of logging
- [x] Add better comments around scheduling - what's supported, specifically?
- [x] Flesh out README/documentation
  - [x] Add a badge for runnion Notion
  - [x] Add a badge for tests
- [x] Get Eric's/Seamus' review
- [x] Fix CI test issue (probably timezone related);
- [x] Implement Seamus' feedback:
  - [x] [Do "select"/"multi-select" need to be
        enums?](https://github.com/fwallacevt/notion-recurring-tasks/commit/95dd55f7b87cd8d762878a6eecf61317bb82b7af#r58538653)
  - [x] Can I set a select/multiselect with id/name/color Null?
  - [x] [Add
        quickstart](https://github.com/fwallacevt/notion-recurring-tasks/commit/fbc5119588e3cf183697d3ac1d83faceb31723d1#r58538760)
- [x] Set status when saving new tasks
- [ ] Need to set timezone in GitHub runner
- [x] Create Notion daily/weekly dashboard
- [ ] Make everything async
  - [ ] Should create new tasks in parallel and be resilient if one fails
- [ ] Improve Schedule utility to return a date if there is no time component
- [ ] Sync with Google calendar
  - [ ] Use [push notifications](https://developers.google.com/calendar/api/guides/push) to sync Google -> Notion
- [ ] Sync with Asana (tasks assigned in Asana get copied over)
- [ ] Resolve todos
- [ ] Implement [Eric's feedback](https://faradayio.slack.com/archives/DN6PMFWAE/p1635116064016800)
  - [ ] Try extracting some smaller functions from the big ones. Hang some off of AST types?
  - [ ] Review [ASTs](https://en.wikipedia.org/wiki/Abstract_syntax_tree) - can I apply?
- [ ] Post on Reddit?
- [ ] Add a code coverage badge (and ignore notion/\* for coverage) (https://github.com/marketplace/actions/dynamic-badges)
- [ ] Extend schedule to support:
  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
  - Every (Jan/Feb/March...) on the (X) day
