# Auto-generated using table2py.py, do not edit except in the sections
# marked with "# == BEGIN CUSTOM ...".
from .default_imports import *  # pylint: disable=unused-wildcard-import

# == BEGIN CUSTOM IMPORTS ==
# Custom imports go here.
# == END CUSTOM IMPORTS ==


class Task(RecordBase):
    "ORM wrapper for row in `tasks`."
    _column_names: ClassVar[Set[str]] = {
        "date_created",
        "done",
        "due_date",
        "last_edited_time",
        "name",
        "priority",
        "schedule",
        "tags",
    }

    _object_columns: ClassVar[Set[str]] = set()

    @classmethod
    def database_id(cls) -> str:
        """Unpack the id of this database from the environment, according to naming convention:
        NOTION_{table name}_DB_ID. For example, an ORM object named "ToDo" will look for
        NOTION_TO_DO_DB_ID in the environment."""
        return os.environ["NOTION_TASKS_DB_ID"]

    def __init__(
        self,
        *,  # Force the remaining parameters to always be keywords.
        date_created: datetime,
        last_edited_time: datetime,
        name: str,
        done: Optional[bool] = None,
        schedule: Optional[str] = None,
        priority: Optional[SelectOptions] = None,
        tags: Optional[List[SelectOptions]] = None,
        due_date: Optional[Union[date, datetime]] = None,
    ):
        # Initialize the superclass first
        super().__init__(name)

        # Make sure we initialize `_updated_columns`, because each of the initializations below depend on it being set.
        self._updated_columns = set()

        # These assignments here are mypy magic: They actually propagate the
        # argument types above onto the the associated member variables,
        # making all of our member variables typed.
        self.__date_created = date_created
        self.__done = done
        self.__schedule = schedule
        self.__priority = priority
        self.__tags = tags
        self.__due_date = due_date
        self.__last_edited_time = last_edited_time
        self.__name = name

        # Finally, save the current state of any object-like columns
        self.save_object_columns()

    @property
    def date_created(self) -> datetime:
        return self.__date_created

    @date_created.setter
    def date_created(self, value: datetime):
        self.__date_created = value
        self.mark_column_changed("date_created")

    @property
    def done(self) -> Optional[bool]:
        return self.__done

    @done.setter
    def done(self, value: Optional[bool]):
        self.__done = value
        self.mark_column_changed("done")

    @property
    def schedule(self) -> Optional[str]:
        return self.__schedule

    @schedule.setter
    def schedule(self, value: Optional[str]):
        self.__schedule = value
        self.mark_column_changed("schedule")

    @property
    def priority(self) -> Optional[SelectOptions]:
        return self.__priority

    @priority.setter
    def priority(self, value: Optional[SelectOptions]):
        self.__priority = value
        self.mark_column_changed("priority")

    @property
    def tags(self) -> Optional[List[SelectOptions]]:
        return self.__tags

    @tags.setter
    def tags(self, value: Optional[List[SelectOptions]]):
        self.__tags = value
        self.mark_column_changed("tags")

    @property
    def due_date(self) -> Optional[Union[date, datetime]]:
        return self.__due_date

    @due_date.setter
    def due_date(self, value: Optional[Union[date, datetime]]):
        self.__due_date = value
        self.mark_column_changed("due_date")

    @property
    def last_edited_time(self) -> datetime:
        return self.__last_edited_time

    @last_edited_time.setter
    def last_edited_time(self, value: datetime):
        self.__last_edited_time = value
        self.mark_column_changed("last_edited_time")

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value
        self.mark_column_changed("name")

    @classmethod
    def deserialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values: Dict[str, Any] = {}
        if "Date created" in values:
            new_values["date_created"] = dateutil.parser.isoparse(
                values["Date created"]["created_time"]
            )
        if "Done" in values:
            new_values["done"] = values["Done"]["checkbox"]
        if "Schedule" in values:
            new_values["schedule"] = (
                None
                if len(values["Schedule"]["rich_text"]) < 1
                else values["Schedule"]["rich_text"][0]["plain_text"]
            )
        if "Priority" in values:
            new_values["priority"] = (
                None
                if values["Priority"]["select"] is None
                else SelectOptions.from_json(values["Priority"]["select"])
            )
        if "Tags" in values:
            new_values["tags"] = [
                SelectOptions.from_json(t) for t in values["Tags"]["multi_select"]
            ]
        if "Due date" in values:
            new_values["due_date"] = (
                None
                if values["Due date"]["date"] is None
                else dateutil.parser.isoparse(values["Due date"]["date"]["start"])
            )
        if "Last edited time" in values:
            new_values["last_edited_time"] = dateutil.parser.isoparse(
                values["Last edited time"]["last_edited_time"]
            )
        if "Name" in values:
            new_values["name"] = (
                None
                if len(values["Name"]["title"]) < 1
                else values["Name"]["title"][0]["plain_text"]
            )
        return new_values

    @classmethod
    def serialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values = {}  # Shallow copy and convert.
        if "done" in values and values["done"] is not None:
            new_values["Done"] = {
                "type": "checkbox",
                "checkbox": values["done"],
            }
        if "schedule" in values and values["schedule"] is not None:
            new_values["Schedule"] = {
                "type": "rich_text",
                "rich_text": [
                    {"type": "text", "text": {"content": values["schedule"]}}
                ],
            }
        if "priority" in values and values["priority"] is not None:
            new_values["Priority"] = {
                "type": "select",
                "select": {
                    k: v
                    for k, v in values["priority"].to_json().items()
                    if v is not None
                },
            }
        if "tags" in values and values["tags"] is not None:
            new_values["Tags"] = {
                "type": "multi_select",
                "multi_select": [
                    {k: v for k, v in i.to_json().items() if v is not None}
                    for i in values["tags"]
                ],
            }
        if "due_date" in values and values["due_date"] is not None:
            new_values["Due date"] = {
                "type": "date",
                "date": {"start": values["due_date"].isoformat()},
            }
        if "name" in values and values["name"] is not None:
            new_values["Name"] = {
                "type": "title",
                "title": [{"type": "text", "text": {"content": values["name"]}}],
            }
        return new_values

    # == BEGIN CUSTOM CODE ==
    @classmethod
    async def check_open_task_exists_by_name(
        cls,
        client: NotionClient,
        task_name: str,
    ) -> bool:
        """Check if any open (incomplete) tasks exist with this name."""
        task = await cls.find_by(
            client,
            {
                "and": [
                    {"property": "Name", "text": {"equals": task_name}},
                    {
                        "property": "Done",
                        "checkbox": {
                            "does_not_equal": True,
                        },
                    },
                ]
            },
        )
        return task is not None

    @classmethod
    async def find_completed_recurring_tasks_since(
        cls,
        client: NotionClient,
        timestamp: datetime,
    ) -> List["Task"]:
        """Get recurring tasks (have a "Schedule") that have been completed (updated) since the given
        timestamp. This will also find previously-completed tasks that have been updated, if they
        were updated for some reason. We return a list of tasks, de-duplicated on name, that should
        be recreated with the next due date on the given schedule."""
        tasks = await cls.find_all_by(
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

        unique_names: Set[str] = set()
        unique_tasks: List["Task"] = []
        for t in tasks:
            if t.name not in unique_names:
                unique_names.add(t.name)
                unique_tasks.append(t)

        return unique_tasks
