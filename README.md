# Notion recurring tasks script

## TODOs

- [x] Add comments/doc strings
- [x] Use Notion DB for keeping track of runs, not a file
- [x] Add gh action to run nightly (date might get messed up because Notion API only compares dates)
- [x] Improve copy functionality (should be able to take arbitrary database and property names, fetch the types, and know
      how to copy from one to the other; e.g. we know how to copy multi-select, select, date, etc.)
- [x] Add gh action to run python job 2x/day
- [x] Remove/archive JS code
- [ ] Improve Cron functionality - cron, or:
  - Daily
  - Weekly (on same day)
  - Monthly
  - Yearly
  - Every (day/weekday)
  - Every (X) weeks on (monday/tuesday/wednesday/...)
  - Every (X) months on the (X) day
  - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
  - Every (X) months on the (first/last) workday
- [ ] Add tests
  - Test schedule utility
  - Test notion recurring tasks (stub out Notion client)?
- [ ] Make schedule attributes read only
- [ ] Run tests on PRs
- [ ] Sync with Google calendar
- [ ] Sync with Asana (tasks assigned in Asana get copied over)
- [ ] Flesh out README/documentation
  - [ ] Add a badge?
- [ ] Post on Reddit?
