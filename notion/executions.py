# Auto-generated using table2py.py, do not edit except in the sections
# marked with "# == BEGIN CUSTOM ...".
from .default_imports import *  # pylint: disable=unused-wildcard-import

# == BEGIN CUSTOM IMPORTS ==
# Custom imports go here.
# == END CUSTOM IMPORTS ==


class Execution(RecordBase):
    "ORM wrapper for row in `executions`."
    _column_names: ClassVar[Set[str]] = {"date_created", "name"}

    _object_columns: ClassVar[Set[str]] = set()

    @classmethod
    def database_id(cls) -> str:
        """Unpack the id of this database from the environment, according to naming convention:
        NOTION_{table name}_DB_ID. For example, an ORM object named "ToDo" will look for
        NOTION_TO_DO_DB_ID in the environment."""
        return os.environ["NOTION_EXECUTIONS_DB_ID"]

    def __init__(
        self,
        *,  # Force the remaining parameters to always be keywords.
        date_created: datetime,
        name: str,
    ):
        # Initialize the superclass first
        super().__init__(name)

        # Make sure we initialize `_updated_columns`, because each of the initializations below depend on it being set.
        self._updated_columns = set()

        # These assignments here are mypy magic: They actually propagate the
        # argument types above onto the the associated member variables,
        # making all of our member variables typed.
        self.__date_created = date_created
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
        if "Name" in values:
            new_values["name"] = values["Name"]["title"][0]["plain_text"]
        return new_values

    @classmethod
    def serialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values = {}  # Shallow copy and convert.
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
    def get_last_execution_time_utc(
        cls,
        client: NotionClient,
    ) -> datetime:
        """Get the last time this ran, in UTC."""
        task = cls.find_newest_by(
            client,
            {},
        )

        if task is not None:
            return task.date_created
        else:
            # If this is the first execution, return a timestamp far in the past so we'll
            # get all tasks completed ever.
            return datetime.fromtimestamp(0)
