# ORM usage

The ORM layer is _*the single most useful*_ feature of this repository. It provides a clean, programmatic interface
between Notion's API and typed Python, and removes the need to parse json or make API calls. Additionally, we provide a
[utility](../notion/db2py.py) that auto-generates ORM wrappers around Notion databases! This means that if you create a
new database, or change the schema of an existing one, _*you can immediately begin developing against it with ZERO
overhead!*_. In order to generate new (or update existing) ORM classes, you will need to have your [development
environment](./developing.md) fully setup.

## Generating or updating ORM classes

To generate new ORM classes, navigate to the Notion directory (from within `notion-recurring-tasks`, run `cd notion/`),
and run:

```sh
python db2py.py $DATABASE_ID $DATABASE_NAME > desired_file_name.py
```

For example:

```sh
python db2py.py 1234 examples > examples.py
```

In general, we advise that file names match database names, since we use the database name to name the ORM object.

To update an existing ORM object, you may not want to immediately overwrite the destination file. For instance, if
you've added custom imports or custom code, overwriting the file will overwrite those changes. In this case, copy the
resulting Python code and manually replace the file contents:

```sh
python db2py.py $DATABASE_ID $DATABASE_NAME | pbcopy
```

## Programmatic usage

The ORM layer provides a clean, simple interface to Notion's databases. For example, we use it to find all recurring
tasks completed since a certain date:

```py
from notion import Task

tasks = Task.find_all_by(
    client,
    {
        "and": [
            {
                "property": "Last edited time",
                "date": {
                    "on_or_after": timestamp.isoformat(),
                },
            },
            {
                "property": "Schedule",
                "text": {
                    "is_not_empty": True,
                },
            },
            {
                "property": "Done",
                "checkbox": {
                    "equals": True,
                },
            },
        ]
    },
)
```

This returns an array of `Task` objects that match the given criteria. The ORM layer provides many utilities in addition
to `find_all_by`.
