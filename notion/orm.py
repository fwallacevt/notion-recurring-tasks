"""Support for using SQLAlchemy to create Python objects that map to rows in
our database.

We basically rolled our own ORM, because we wanted something that was
lightweight, typed and asynchronous."""

from abc import ABCMeta, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
from typing import (
    Any,
    Callable,
    ClassVar,
    List,
    Mapping,
    Optional,
    Set,
    Type,
    TypeVar,
)

from .notion_client import NotionClient


def now_utc() -> datetime:
    """The current time in UTC."""
    return datetime.now(timezone.utc)


# Type variable used for methods like `find_by_id_or_raise` that need to be declarated as
# returning an instance of what whatever class they're called on.
T = TypeVar("T", bound="RecordBase")


class RecordBase(metaclass=ABCMeta):
    """Base class for ORM-like database record classes.

    This handles the minimum functionality because adding more would cause
    challenges with mypy. Any additional necessary functionality should be
    added in sub classes."""

    # Our title column.
    __title: str

    # A class variable with all column names
    _column_names: ClassVar[Set[str]]

    # Columns updated since last update
    _updated_columns: Set[str]

    # Columns with object types (e.g. `Any`, `List[...]`)
    _object_columns: ClassVar[Set[str]]
    _object_column_values: Any

    @abstractmethod
    def __init__(self, title: str):
        """Called by subclasses to specify the `title` column."""
        self.title = title

    def __str__(self) -> str:
        return f"{type(self).__name__} {self.title}"

    @property
    def title(self) -> str:
        return self.__title

    @title.setter
    def title(self, value: str):
        self.__title = value

    @classmethod
    def database_id(cls: Type[T]) -> str:
        """Unpack the id of this database from the environment, according to naming convention:
        NOTION_{table name}_DB_ID. For example, an ORM object named "ToDo" will look for
        NOTION_TO_DO_DB_ID in the environment."""
        raise Exception(f"ORM {cls} must implement database_id()")

    @classmethod
    def find_all_by(
        cls: Type[T],
        client: NotionClient,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> List[T]:
        """Look up records by arbitrary things."""
        result = client.query_db(database_id=cls.database_id(), filter=filter)
        return cls.unpack_records(result)

    @classmethod
    def find_by(
        cls: Type[T],
        client: NotionClient,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> Optional[T]:
        """Look up a record by arbitrary things."""
        result = client.query_db(
            database_id=cls.database_id(), filter=filter, page_size=1
        )
        # Get the first record, or None
        return cls.unpack_record(next(iter(result), None))

    @classmethod
    def find_by_or_raise(
        cls: Type[T],
        client: NotionClient,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> T:
        record = cls.find_by(client=client, filter=filter)
        if record is not None:
            return record
        else:
            raise Exception(f"cannot find {cls.__name__} with filter {filter}")

    @classmethod
    def find_newest_by(
        cls: Type[T],
        client: NotionClient,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> Optional[T]:
        """Look up a record by arbitrary things, first by created_time."""
        result = client.query_db(
            database_id=cls.database_id(),
            filter=filter,
            sorts=[{"timestamp": "created_time", "direction": "descending"}],
            page_size=1,
        )
        return cls.unpack_record(next(iter(result), None))

    @classmethod
    def find_newest_by_or_raise(
        cls: Type[T],
        client: NotionClient,
        filter: Optional[Mapping[str, Any]] = None,
    ) -> T:
        record = cls.find_newest_by(client=client, filter=filter)
        if record is not None:
            return record
        else:
            raise Exception(
                f"cannot find {cls.__name__}. Filter: {str(filter)}"
            )

    @classmethod
    def deserialize_values(
        cls: Type[T], values: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Deserialize each value in `values` if necessary. We override this in generated subclasses.

        This is used to handle types like per-table `Status` enumerations, which
        are always stored as strings, but which need to be deserialized into a
        variety of different types. The standard `register_adapter` code doesn't
        seem to handle this case, but maybe I'm missing something."""
        return values

    @classmethod
    def serialize_values(
        cls: Type[T], values: Mapping[str, Any]
    ) -> Mapping[str, Any]:
        """Serialize each value in `values` if necessary. We override this in
        generated subclasses."""
        return values

    @classmethod
    def unpack_record(
        cls: Type[T],
        mapping: Optional[Mapping[str, Any]],
    ) -> Optional[T]:
        if mapping is not None:
            # Hack around the type system long enough enough to call our derived
            # class constructor with the untyped mapping we got from SQLAlchemy.
            cls_untyped: Callable = cls
            return cls_untyped(**cls.deserialize_values(mapping["properties"]))
        else:
            return None

    @classmethod
    def unpack_records(
        cls: Type[T], records: List[Mapping[str, Any]]
    ) -> List[T]:
        typed: List[T] = []
        for mapping in records:
            # Hack around the type system long enough enough to call our derived
            # class constructor with the untyped mapping we got from SQLAlchemy.
            cls_untyped: Callable = cls
            typed.append(
                cls_untyped(**cls.deserialize_values(mapping["properties"]))
            )

        return typed

    def insertable_values(self) -> Mapping[str, Any]:
        """Column names and values for all updatable columns in the database.

        You may need to override this if you add custom member variables that
        don't correspond to database columns."""

        # Make a copy so our callers don't accidentally update this object.
        return dict({k: getattr(self, k) for k in self._column_names})

    def insert(self, client: NotionClient):
        """Insert this record into the database."""
        client.add_page_to_db(
            self.__class__.database_id(),
            self.serialize_values(self.insertable_values()),
        )

    def save_object_columns(self):
        """Save the value of all the object-type columns, for later reference."""
        self._object_column_values = {
            c: deepcopy(getattr(self, c)) for c in self._object_columns
        }

    def mark_column_changed(self, column_name: str):
        if column_name not in self._updated_columns:
            self._updated_columns.add(column_name)

    def updatable_values(self) -> Mapping[str, Any]:
        """Column names and values for all updated columns in the database."""
        # We update anything in _update_columns, and anything in _object_columns that we think has changed. We check
        # this by comparing current value to the most recent saved value (in self._object_column_values). Since these
        # are object-like (e.g. referred to by reference), they may be unordered, and thus we may falsely update fields
        # without them having changed. This is not a problem - we only care that we _always_ update when the field has
        # changed, which is guaranteed by equality regardless of ordering.
        values = {
            **{k: getattr(self, k) for k in self._updated_columns},
            **{
                k: getattr(self, k)
                for k in self._object_columns
                if self._object_column_values.get(k) != getattr(self, k)
            },
        }

        # Remove unchangeable attributes. Notion handles these itself
        if "created_time" in values:
            del values["created_time"]
        if "last_edited_time" in values:
            del values["last_edited_time"]
        return values

    def update(self, client: NotionClient):
        """Update this record in the database with the values we have in memory."""
        # TODO(fwallace): Implement this
        # client.update()
        # await conn.inner.execute(
        #     self.table.update(None)
        #     .where(self.table.c.id == self.id)
        #     .values(**self.serialize_values(self.updatable_values()))
        # )

        # # Clear updated values and save current state of object-like columns
        # self._updated_columns.clear()
        # self.save_object_columns()
        raise NotImplementedError(f"RecordBase must implement `update`.")
