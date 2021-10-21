# Notion extensions

This project aims to extend [Notion's](https://www.notion.so/product) functionality to work more broadly for a variety
of users and provide a skeleton for other developers to create well-formulated extensions using [Notion's
API](https://developers.notion.com/).

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
easily be stored to be passed to actions, and schedules or triggers can be customized. For an example of setting up
actions, see below.
TODO(fwallace): Link to recurring tasks for todo lists section (below).

This project's primary value is as an example for others to use when developing against Notion's API.

## Features

The following features are supported by this project.

### Recurring tasks for todo lists

Description... (also need to create a Notion template)

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
- [ ] Resolve todos
- [x] Add better comments around scheduling - what's supported, specifically?
- [ ] Flesh out README/documentation
  - [ ] Add a badge?
  - [ ] Add a code coverage badge (and ignore notion/ for coverage)
- [ ] Sync with Google calendar
- [ ] Sync with Asana (tasks assigned in Asana get copied over)
- [ ] Post on Reddit?
- [ ] Extend schedule to support:
  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
  - Every (Jan/Feb/March...) on the (X) day
