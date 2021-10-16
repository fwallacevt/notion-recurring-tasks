# Auto-generated using table2py.py, do not edit except in the sections
# marked with "# == BEGIN CUSTOM ...".
from .default_imports import *  # pylint: disable=unused-wildcard-import

# == BEGIN CUSTOM IMPORTS ==
# Custom imports go here.
# == END CUSTOM IMPORTS ==


class Status(Enum):
    "Enum for Status values, mapping name to id."

    TO_DO = "955347da-4f72-43cb-94f9-83671b141073"
    DOING = "afb8057f-c5cb-4012-9aa6-83c64d9de472"
    DONE = "fa612bba-7f5e-4549-8fc3-966ecd9c46b3"


class Priority(Enum):
    "Enum for Priority values, mapping name to id."

    HIGH = "9fd52657-92f8-4c6e-94a2-196331fc13f0"
    MEDIUM = "2d89445a-80eb-4be8-9177-3559e736e69c"
    LOW = "f8de6404-18c0-48bd-a784-add8f4d9239c"
    NONE = "07242016-f132-4b9d-9489-5ca7b7774ffd"


class Tags(Enum):
    "Enum for Tags values, mapping name to id."

    HOUSE = "63659d8d-27e0-43f0-a29a-ecba965342d4"
    ELECTRICAL = "2151a861-9f25-4bf6-979f-0f5c0efd5b5a"
    PERSONAL = "c2f72d3c-90ed-488f-902b-636bf13b7ef7"


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
        "status",
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
        status: Optional[Status] = None,
        schedule: Optional[str] = None,
        priority: Optional[Priority] = None,
        tags: Optional[List[Tags]] = None,
        due_date: Optional[datetime] = None,
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
        self.__status = status
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
    def status(self) -> Optional[Status]:
        return self.__status

    @status.setter
    def status(self, value: Optional[Status]):
        self.__status = value
        self.mark_column_changed("status")

    @property
    def schedule(self) -> Optional[str]:
        return self.__schedule

    @schedule.setter
    def schedule(self, value: Optional[str]):
        self.__schedule = value
        self.mark_column_changed("schedule")

    @property
    def priority(self) -> Optional[Priority]:
        return self.__priority

    @priority.setter
    def priority(self, value: Optional[Priority]):
        self.__priority = value
        self.mark_column_changed("priority")

    @property
    def tags(self) -> Optional[List[Tags]]:
        return self.__tags

    @tags.setter
    def tags(self, value: Optional[List[Tags]]):
        self.__tags = value
        self.mark_column_changed("tags")

    @property
    def due_date(self) -> Optional[datetime]:
        return self.__due_date

    @due_date.setter
    def due_date(self, value: Optional[datetime]):
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
    def deserialize_values(
        cls, values: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        new_values: Dict[str, Any] = {}
        if "Date created" in values:
            new_values["date_created"] = dateutil.parser.isoparse(
                values["Date created"]["created_time"]
            )
        if "Done" in values:
            new_values["done"] = values["Done"]["checkbox"]
        if "Status" in values:
            new_values["status"] = Status[
                enum_name_to_alias(values["Status"]["select"]["name"])
            ]
        if "Schedule" in values:
            new_values["schedule"] = values["Schedule"]["rich_text"][0][
                "plain_text"
            ]
        if "Priority" in values:
            new_values["priority"] = Priority[
                enum_name_to_alias(values["Priority"]["select"]["name"])
            ]
        if "Tags" in values:
            new_values["tags"] = [
                Tags[enum_name_to_alias(t["name"])]
                for t in values["Tags"]["multi_select"]
            ]
        if "Due date" in values:
            new_values["due_date"] = dateutil.parser.isoparse(
                values["Due date"]["date"]["start"]
            )
        if "Last edited time" in values:
            new_values["last_edited_time"] = dateutil.parser.isoparse(
                values["Last edited time"]["last_edited_time"]
            )
        if "Name" in values:
            new_values["name"] = values["Name"]["title"][0]["plain_text"]
        return new_values

    @classmethod
    def serialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values = {}  # Shallow copy and convert.
        if "done" in values:
            new_values["Done"] = {
                "type": "checkbox",
                "checkbox": values["done"],
            }
        if "status" in values:
            new_values["Status"] = {
                "type": "select",
                "select": {"id": (values["status"]).value},
            }
        if "schedule" in values:
            new_values["Schedule"] = {
                "type": "rich_text",
                "rich_text": [
                    {"type": "text", "text": {"content": values["schedule"]}}
                ],
            }
        if "priority" in values:
            new_values["Priority"] = {
                "type": "select",
                "select": {"id": (values["priority"]).value},
            }
        if "tags" in values:
            new_values["Tags"] = {
                "type": "multi_select",
                "multi_select": [{"id": v.value} for v in values["tags"]],
            }
        if "due_date" in values:
            new_values["Due date"] = {
                "type": "date",
                "date": {"start": values["due_date"].isoformat()},
            }
        if "name" in values:
            new_values["Name"] = {
                "type": "title",
                "title": [
                    {"type": "text", "text": {"content": values["name"]}}
                ],
            }
        return new_values

    # == BEGIN CUSTOM CODE ==
    @classmethod
    def check_open_task_exists_by_name(
        cls,
        client: NotionClient,
        task_name: str,
    ) -> bool:
        """Check if any open (incomplete) tasks exist with this name."""
        task = cls.find_by(
            client,
            {
                "and": [
                    {"property": "Name", "text": {"equals": task_name}},
                    {
                        "property": "Done",
                        "checkbox": {
                            "equals": False,
                        },
                    },
                ]
            },
        )
        return task is not None

    @classmethod
    def find_completed_recurring_tasks_since(
        cls,
        client: NotionClient,
        timestamp: datetime,
    ) -> Set["Task"]:
        """Get recurring tasks (have a "Schedule") that have been completed (updated) since the given
        timestamp. This will also find previously-completed tasks that have been updated, if they
        were updated for some reason. We return a list of tasks, de-duplicated on name, that should
        be recreated with the next due date on the given schedule."""
        tasks = cls.find_all_by(
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

        unique_names: Set[str] = Set()
        unique_tasks: Set["Task"] = Set()
        for t in tasks:
            if t.name not in unique_names:
                unique_names.add(t.name)
                unique_tasks.add(t)

        return unique_tasks
