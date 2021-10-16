"""A script for converting a Notion "database" (table) into ORM declarations.

First, ensure that `NOTION_API_KEY` is set in your environment, and authenticated
to the table you're interested in.

Then run this as:

    python db2py.py $NOTION_DATABASE_ID

...and it will print out Python code on stdout."""

import sys

sys.path.append("..")

from abc import ABCMeta, abstractmethod
import asyncio
from os import environ, path
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from utils.naming import (
    enum_name_to_alias,
    property_name_to_column_name,
    property_to_enum_class_name,
    table_to_class_name,
)
from utils.serde import Deserializable

from notion.notion_client import NotionClient


class CustomCode:
    """Custom code snippets to inject into an ORM class."""

    def __init__(self, imports: str, code: str, has_custom_status_type: bool):
        self.imports = imports
        self.code = code
        self.has_custom_status_type = has_custom_status_type

    @staticmethod
    def default() -> "CustomCode":
        """The default custom code for a new file."""
        return CustomCode(
            imports="# Custom imports go here.",
            code="    # Custom code goes here.",
            has_custom_status_type=False,
        )

    @staticmethod
    def for_table(table: str) -> "CustomCode":
        """The custom code for the specified table.

        We'll fetch this from disk if it already exists, or fill it in with
        sensible defaults."""
        source_path = f"./{table}.py"
        if path.isfile(source_path):
            with open(source_path, "r") as f:
                source = f.read()
                matches = re.search(
                    "# == BEGIN CUSTOM IMPORTS ==\n(.*)\n# == END CUSTOM IMPORTS ==.*# == BEGIN CUSTOM CODE ==\n(.*)",
                    source,
                    re.DOTALL,
                )
                has_custom_status_type = (
                    re.search("^class Status", source, re.MULTILINE)
                    is not None
                )
                if matches is not None:
                    return CustomCode(
                        imports=matches[1],
                        code=matches[2],
                        has_custom_status_type=has_custom_status_type,
                    )
        return CustomCode.default()


class PropertyType(metaclass=ABCMeta):
    """A Notion data type."""

    @abstractmethod
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary."""
        self.name = json["name"]
        self.type = json["type"]

    @staticmethod
    def from_notion_json(json: Any) -> "PropertyType":
        """Parse a Notion data type specified as JSON."""
        type = json["type"]
        if type == "date":
            return DateType(json)
        elif type == "last_edited_time":
            return TimestampType(json)
        elif type == "created_time":
            return TimestampType(json)
        elif type == "select":
            return SelectType(json)
        elif type == "multi_select":
            return MultiSelectType(json)
        elif type == "rich_text":
            return RichTextType(json)
        elif type == "checkbox":
            return CheckboxType(json)
        elif type == "title":
            return RichTextType(json)
        raise Exception(f"Unknown Notion type: {json}")

    def is_internally_mutable(self) -> bool:
        """An internally mutable type is any type that can be mutated in place
        without completely replacing the object. For example, arrays, dicts and
        objects are internally mutable. Integers, strings, etc., are not."""
        return False

    @abstractmethod
    def notion_type(self) -> str:
        """The type to pass to Notion."""
        pass

    @abstractmethod
    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        pass

    @abstractmethod
    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        pass

    @abstractmethod
    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        pass

    def has_enum(self) -> bool:
        """Does this type have an a set of values? If so, what are they?"""
        return False

    def enum_class_definition(self) -> str:
        """Take the allowed values for this column and turn them into a valid
        enum class, if applicable."""
        raise Exception("datatype {self} does not need an enum.")


class CheckboxType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "%3E%3Bk%7C",
            "name": "Done",
            "type": "checkbox",
            "checkbox": {}
        }"""
        super().__init__(json)

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return "bool"

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""{value_expr}["{self.type}"]"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        return value_expr


class RichTextType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "Gvh_",
            "name": "Parent",
            "type": "rich_text",
            "rich_text": {}
        }"""
        super().__init__(json)

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return "str"

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""{value_expr}["{self.type}"][0]["plain_text"]"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        return f"""[{{"type": "text", "text": {{"content": {value_expr}}}}}]"""


class DateType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "'Y6%3C",
            "name": "Date Created",
            "type": "created_time",
            "created_time": {}
        }"""
        super().__init__(json)

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return "datetime"

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""dateutil.parser.isoparse({value_expr}["{self.type}"]["start"])"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        return f"""{{"start": {value_expr}.isoformat()}}"""


class TimestampType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "'Y6%3C",
            "name": "Date Created",
            "type": "created_time",
            "created_time": {}
        }"""
        super().__init__(json)

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return "datetime"

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""dateutil.parser.isoparse({value_expr}["{self.type}"])"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        raise Exception("datatype {self} does not know how to serialize.")


class SelectType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "vpw_",
            "name": "Priority",
            "type": "select",
            "select": {
                "options": [
                    {
                        "id": "9fd52657-92f8-4c6e-94a2-196331fc13f0",
                        "name": "High",
                        "color": "blue"
                    },
                    {
                        "id": "2d89445a-80eb-4be8-9177-3559e736e69c",
                        "name": "Medium",
                        "color": "red"
                    },
                    {
                        "id": "f8de6404-18c0-48bd-a784-add8f4d9239c",
                        "name": "Low",
                        "color": "pink"
                    },
                    {
                        "id": "07242016-f132-4b9d-9489-5ca7b7774ffd",
                        "name": "None",
                        "color": "green"
                    }
                ]
            }
        }"""
        super().__init__(json)
        self.options = json[self.type]["options"]

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return f"{property_to_enum_class_name(self.name)}"

    def has_enum(self) -> bool:
        """Does this type have an a set of values? If so, what are they?"""
        return True

    def enum_class_definition(self) -> str:
        """Take the allowed values for this column and turn them into a valid
        enum class, if applicable."""
        enum_values = f"\n    ".join(
            [
                f"""{enum_name_to_alias(o["name"])} = "{o["id"]}\""""
                for o in self.options
            ]
        )
        return f"""\
class {property_to_enum_class_name(self.name)}(Enum):
    "Enum for {self.name} values, mapping name to id."

    {enum_values}"""

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""{property_to_enum_class_name(self.name)}[enum_name_to_alias({value_expr}["{self.type}"]["name"])]"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        return f"""{{"id": ({value_expr}).value}}"""


class MultiSelectType(PropertyType):
    def __init__(self, json: Any):
        """Initialize the type, unpacking values as necessary. json will look like:
        {
            "id": "vr%7Bp",
            "name": "Tags",
            "type": "multi_select",
            "multi_select": {
                "options": [
                    {
                        "id": "63659d8d-27e0-43f0-a29a-ecba965342d4",
                        "name": "House",
                        "color": "red"
                    },
                    {
                        "id": "2151a861-9f25-4bf6-979f-0f5c0efd5b5a",
                        "name": "Electrical",
                        "color": "default"
                    },
                    {
                        "id": "c2f72d3c-90ed-488f-902b-636bf13b7ef7",
                        "name": "Personal",
                        "color": "pink"
                    }
                ]
            }
        }"""
        super().__init__(json)
        self.options = json[self.type]["options"]

    def notion_type(self) -> str:
        """The type to pass to Notion."""
        return self.type

    def python_type(self) -> str:
        """The type to use for our member variable in Python."""
        return f"List[{property_to_enum_class_name(self.name)}]"

    def has_enum(self) -> bool:
        """Does this type have an a set of values? If so, what are they?"""
        return True

    def enum_class_definition(self) -> str:
        """Take the allowed values for this column and turn them into a valid
        enum class, if applicable."""
        enum_values = f"\n    ".join(
            [
                f"""{enum_name_to_alias(o["name"])} = "{o["id"]}\""""
                for o in self.options
            ]
        )
        return f"""\
class {property_to_enum_class_name(self.name)}(Enum):
    "Enum for {self.name} values, mapping name to id."

    {enum_values}"""

    def deserialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a database value, and return an
        expression that returns a local value."""
        return f"""[{property_to_enum_class_name(self.name)}[enum_name_to_alias(t["name"])] for t in {value_expr}["{self.type}"]]"""

    def serialization_expr(self, value_expr: str) -> str:
        """Take an expression returning a local value, and return an
        expression that returns a database value."""
        # Here, we need to return a _list of objects_, of shape {"id": enum id}
        id_expressions = [f"""[{{"id": v.value}} for v in {value_expr}]"""]
        return f"""{",".join(id_expressions)}"""


class Column:
    """A Notion "property" (column)."""

    def __init__(self, name: str, is_nullable: bool, data_type: Any):
        self.notion_name = name
        self.name = property_name_to_column_name(name)
        self.is_nullable = is_nullable
        self.data_type = PropertyType.from_notion_json(data_type)

    def notion_column(self) -> str:
        """An Notion property declaration for this column."""
        return f"{self.data_type.notion_type()},"

    def init_param(self) -> Tuple[str, bool]:
        """A constructor type parameter for this column. If a default value
        is included, the second result value will be `True`."""
        ty = self.data_type.python_type()

        if self.is_nullable:
            default = " = None"
            has_default = True
        else:
            # Otherwise, it's a required field without a default value.
            default = ""
            has_default = False

        if self.is_nullable and ty != "Any":
            return (f"{self.name}: Optional[{ty}]{default},", has_default)
        else:
            return (f"{self.name}: {ty}{default},", has_default)

    def init_assignment(self) -> str:
        """A __init__ body assignment for this column."""
        if self.name in ["created_at", "updated_at"]:
            return f"if {self.name} is None:\n            {self.name} = now_utc()\n        self.{self.name} = {self.name}"
        # object-like columns don't have setters
        if self.data_type.is_internally_mutable():
            return f"self.{self.name} = {self.name}"
        # use __{name} instead of {name} so that initializing the column doesn't
        # call the setter (setter adds the column to _updated_columns)
        return f"self.__{self.name} = {self.name}"

    def property_getter_setter(self) -> str:
        """Return a string to define this column as a property on the parent class. In addition to typing,
        this supports updating self._updated_columns when a property is changed."""
        # We don't bother for reference-based properties, since they will always be updated.
        if self.data_type.is_internally_mutable():
            return ""

        ty = self.data_type.python_type()

        type_str = ty
        if self.is_nullable and ty != "Any":
            type_str = f"Optional[{ty}]"

        return f"""
    @property
    def {self.name}(self) -> {type_str}:
        return self.__{self.name}
        
    @{self.name}.setter
    def {self.name}(self, value: {type_str}):
        self.__{self.name} = value
        self.mark_column_changed("{self.name}")"""

    def deserialization_expr(self) -> Optional[str]:
        """Return an optional `"name": deserialize_func(orig.name)` code fragment if
        one will be needed."""
        lvalue = f"values[{repr(self.notion_name)}]"
        svalue = f"new_values[{repr(self.name)}]"
        return f"""\
        if {repr(self.notion_name)} in values:
            {svalue} = {self.data_type.deserialization_expr(lvalue)}
"""

    def serialization_expr(self) -> Optional[str]:
        """Return an optional `"name": serialize_func(orig.name)` code fragment
        if one will be needed."""
        # These are fields that Notion sets on its end
        if self.notion_name.lower() in ["last edited time", "date created"]:
            return None

        lvalue = f"values[{repr(self.name)}]"
        svalue = f"new_values[{repr(self.notion_name)}]"
        return f"""\
        if {repr(self.name)} in values:
            {svalue} = {{
                "type": "{self.data_type.notion_type()}",
                "{self.data_type.notion_type()}": {self.data_type.serialization_expr(lvalue)},
            }}
"""

    def enum_class_definition(self) -> Optional[str]:
        if self.data_type.has_enum():
            return self.data_type.enum_class_definition()
        else:
            return None


class Table:
    """A Notion database schema."""

    name: str
    columns: List[Column]

    def __init__(self, name: str, columns: Any):
        self.name = name
        self.columns = list(Column(**col) for col in columns)

    def class_name(self) -> str:
        """Notion allows multiple databases with the same name, so we expect the user
        to have given us a properly formatted table name (snake case)."""
        return table_to_class_name(self.name)

    def python_code(self, custom: CustomCode) -> str:
        """Generate source code for this table."""
        class_name = self.class_name()
        table_name = self.name

        # Define properties for all columns, with types
        properties_str = "\n    ".join(
            c.property_getter_setter() for c in self.columns if c.name != "id"
        )

        # Initialization parameters need to be ordered with mandatory parameters
        # before optional parameters.
        all_init_params = list(c.init_param() for c in self.columns)
        required_init_params = list(
            p for (p, has_default) in all_init_params if not has_default
        )
        optional_init_params = list(
            p for (p, has_default) in all_init_params if has_default
        )
        init_params = "\n        ".join(
            required_init_params + optional_init_params
        )

        # Now build init assignments. We separate column assignments from foreign key assignments,
        # which are explicitly initialized to None.
        init_assignments = "\n        ".join(
            [c.init_assignment() for c in self.columns if c.name != "id"]
        )

        # Break this out to handle the empty list case
        internally_mutable_columns = [
            c for c in self.columns if c.data_type.is_internally_mutable()
        ]
        _object_columns_str = (
            "set()"
            if len(internally_mutable_columns) == 0
            else f"{{{', '.join(map(repr, sorted({c.name for c in internally_mutable_columns})))}}}"
        )

        # If we have any members requiring custom deserialization, override
        # `deserialize_values`.
        deserialization_exprs = list(
            filter(None, (col.deserialization_expr() for col in self.columns))
        )
        deserialize_values_str = f"""
    @classmethod
    def deserialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values: Dict[str, Any] = {{}}
{"".join(deserialization_exprs)}\
        return new_values
"""

        # If we have any members requiring custom serialization, override
        # `serialize_values`.
        serialization_exprs = list(
            filter(None, (col.serialization_expr() for col in self.columns))
        )
        serialize_values_str = f"""
    @classmethod
    def serialize_values(cls, values: Mapping[str, Any]) -> Mapping[str, Any]:
        new_values = {{}} # Shallow copy and convert.
{"".join(serialization_exprs)}\
        return new_values
"""

        # If we have any members requiring enum classes, override
        # define them.
        enum_classes = list(
            filter(None, (col.enum_class_definition() for col in self.columns))
        )
        if not enum_classes:
            enum_class_str = ""
        else:
            enum_class_str = "\n\n".join(enum_classes)

        return f"""# Auto-generated using table2py.py, do not edit except in the sections
# marked with "# == BEGIN CUSTOM ...".
from .default_imports import *  # pylint: disable=unused-wildcard-import

# == BEGIN CUSTOM IMPORTS ==
{custom.imports}
# == END CUSTOM IMPORTS ==

{enum_class_str}

class {class_name}(RecordBase):
    "ORM wrapper for row in `{table_name}`."
    _column_names: ClassVar[Set[str]] = {{{", ".join(map(repr, sorted({c.name for c in self.columns})))}}}

    _object_columns: ClassVar[Set[str]] = {_object_columns_str}

    @classmethod
    def database_id(cls) -> str:
        \"\"\"Unpack the id of this database from the environment, according to naming convention:
        NOTION_{{table name}}_DB_ID. For example, an ORM object named "ToDo" will look for
        NOTION_TO_DO_DB_ID in the environment.\"\"\"
        return os.environ["NOTION_{table_name.replace(" ", "_").upper()}_DB_ID"]

    def __init__(
        self,
        *,  # Force the remaining parameters to always be keywords.
        {init_params}
    ):
        # Initialize the superclass first
        super().__init__(name)

        # Make sure we initialize `_updated_columns`, because each of the initializations below depend on it being set.
        self._updated_columns = set()

        # These assignments here are mypy magic: They actually propagate the
        # argument types above onto the the associated member variables,
        # making all of our member variables typed.
        {init_assignments}

        # Finally, save the current state of any object-like columns
        self.save_object_columns()

    {properties_str}
    {deserialize_values_str}
    {serialize_values_str}
    # == BEGIN CUSTOM CODE ==
{custom.code}"""


def process_column(
    name: str,
    data_type: Any,
) -> Dict[str, Any]:
    """
    Here we transform some column data from Notion into the format which
    this script requires to generate the ORM. It's very similar dbcrossbar's
    column schema, but it includes an extra field: "default_value".
    """
    # A notion schema for the column. Notion has _*VERY*_ loose restrictions on
    # databases, meaning basically anything can be null. I happen to know a couple
    # columns actually won't be, so I hardcode those here.
    non_nullable_columns = ["date created", "last edited time", "name"]
    return {
        "name": name,
        "is_nullable": name.lower() not in non_nullable_columns,
        "data_type": data_type,
    }


def get_columns_json(table_id: str, table_name: str) -> Mapping[str, Any]:
    """
    Fetch the schema from Notion, as json
    """
    client = NotionClient(api_key=environ["NOTION_API_KEY"])
    json = client.retrieve_db(table_id)
    properties = json["properties"]

    return {
        "name": table_name,
        "columns": [process_column(k, v) for k, v in properties.items()],
    }


async def generate_orm_decls(table_id: str, table_name: str) -> str:
    output = get_columns_json(table_id, table_name)
    table = Table(**output)
    custom = CustomCode.for_table(table_name)
    return table.python_code(custom)


async def print_orm_decls(table_id: str, table_name: str):
    print(await generate_orm_decls(table_id, table_name))


if __name__ == "__main__":
    # Retrieves a Notion database object, and unpacks it:
    #   https://developers.notion.com/reference/database
    # The json includes a variety of fields, but we really only care about
    # the properties. Since Notion will let you make multiple databases with
    # the same name, we have to have the user set the names.
    argv = sys.argv
    if len(argv) != 3:
        print("USAGE: python db2py.py $TABLE_ID $TABLE_NAME", file=sys.stderr)
        sys.exit(1)
    asyncio.run(print_orm_decls(argv[1], argv[2]))
