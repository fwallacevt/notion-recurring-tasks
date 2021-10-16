from abc import ABCMeta, abstractmethod
from typing import Any, List
from datetime import datetime
from uuid import UUID


# TODO(fwallace): We could write something that will auto-generate these classes (essentially a simple ORM layer)
# based on the schema returned by https://developers.notion.com/reference/retrieve-a-database. The idea would be
# to parse the schema and generate a typed class based on that, with functions to serialize and deserialize
# values accordingly.
class PropertyType(metaclass=ABCMeta):
    """A Notion property type. Possible types are listed
    [here](https://developers.notion.com/reference/database#property-object)."""

    @abstractmethod
    def from_json(self, json: Any):
        pass

    @staticmethod
    def from_notion_json(json: Any) -> "PropertyType":
        """Parse Notion format json, and return the appropriate type handler. Possible types are:
        "rich_text"
        "number"
        "select"
        "multi_select"
        "date"
        "formula"
        "relation"
        "rollup"
        "title"
        "people"
        "files"
        "checkbox"
        "url"
        "email"
        "phone_number"
        "created_time"
        "created_by"
        "last_edited_time"
        "last_edited_by"
        """
        # Notion puts the data in a field named with `type` for each property. For example:
        # "Done": {
        #     "id": "%3E%3Bk%7C",
        #     "type": "checkbox",
        #     "checkbox": false
        # }
        # We can unpack the values we care about for each type this way
        key_name = json["type"]
        if key_name == "date":
            return DateType(json[key_name])
        elif json[key_name] == "last_edited_time":
            return TimestampType(json[key_name])
        elif json[key_name] == "created_time":
            return TimestampType(json[key_name])
        elif json[key_name] == "select":
            return SelectType(json[key_name])
        elif json[key_name] == "multi_select":
            return MultiSelectType(json[key_name])
        elif json[key_name] == "rich_text":
            return RichTextType(json[key_name])
        elif json[key_name] == "checkbox":
            return CheckboxType(json[key_name])
        elif json[key_name] == "title":
            return RichTextType(json[key_name])
        raise Exception(f"Unknown Notion type: {json}")


class CheckboxType(PropertyType):
    # Whether the checkbox has been checked
    checked: bool

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. Json should simply
        be a boolean here."""
        self.text = json


class RichTextType(PropertyType):
    # The text value. For now, we assume that these are simple text fields, and not richtext.
    text: str

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. These have shape like:
        [
            {
                "type": "text",
                "text": {
                    "content": "Every week on Thursday",
                    "link": null
                },
                "annotations": {
                    "bold": false,
                    "italic": false,
                    "strikethrough": false,
                    "underline": false,
                    "code": false,
                    "color": "default"
                },
                "plain_text": "Every week on Thursday",
                "href": null
            }
        ]
        """
        self.text = json["text"]["plain_text"]


class SelectType(PropertyType):
    # The value that has been selected
    selected_id: UUID
    selected_name: str

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. These have shape like:
        {
            "id": "9fd52657-92f8-4c6e-94a2-196331fc13f0",
            "name": "High",
            "color": "blue"
        }
        """
        self.selected_id = UUID(json["id"])
        self.selected_name = json["name"]


class MultiSelectType(PropertyType):
    # The values that have been selected
    selected: List[SelectType]

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. These have shape like:
        [
            {
                "id": "63659d8d-27e0-43f0-a29a-ecba965342d4",
                "name": "House",
                "color": "red"
            }
        ]
        """
        self.selected = [SelectType.from_json(s) for s in json]


class DateType(PropertyType):
    # The date we're interested in
    date: datetime

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. These have shape like:
        "date": {
            "start": "2021-10-14",
            "end": null
        }
        """

        # First, check that it's not a date range (for now, we only support dates)
        # TODO(fwallace): Support date ranges
        if json["end"] != None:
            raise Exception(
                f"DateType does not support date ranges - please implement if desired"
            )

        self.date = datetime.fromisoformat(json["start"])


class TimestampType(PropertyType):
    # The date we're interested in
    timestamp: datetime

    def from_json(self, json: Any):
        """Parse the given json and construct a properly formatted Python type. These have shape like:
        "2021-10-14T15:59:00.000Z"
        """

        # TODO(fwallace): This won't actually work with the 'Z' at the end - figure out how to convert to a UTC
        # timestamp
        self.timestamp = datetime.fromisoformat(json)


class NotionPage(metaclass=ABCMeta):
    # TODO(fwallace): Is there anything we can enforce here, to make this type actually mean something?
    pass


# We want to take a blob of json from Notion, and return a properly typed Python object for whichever
# page we're interested in
# Similarly, we want to be able to construct properly-typed python objects easily

# I need to actually sit down and design this, and not when I'm about to pass out from exhaustion...
# For now, I can probably focus on the db component, I guess?

# What should our python objects look like?

# Okay, what do I want this to look like? What are the requirements?
# Load things from Notion into typed Python classes
# Transform typed Python classes into Notion objects (e.g. have a "create" method)
# I think the answer is to make an ORM class that will deserialize Notion json -> typed Python, and has:
#
#   - "find_all_by_...", "find_newest_by...", "find_by_or_raise...", etc.
#       - Takes a notion client
#       - Takes a notion db id? These classes will correspond to a particular db, but we want those kept secret so can't
#         commit
#       - Alternatively we could have an environ key we expect to exist - maybe we'll go this route
#       - Need a class-oriented way of deserializing the Notion json; similar to serde.json
#       - Architecture should mirror `orm.py`
#       - Auto-generation is a nice-to-have in the future; ignore for now
#   - "insert..."
#       - Takes a notion client
#       - Serializes the object into appropriately-formatted Notion json
#       - Sets the db as the parent
#       - Invokes notion client
#   - etc.
#
# So, ORM class needs to provide shared functionality to:
#   - Deserialize records, based on notion type
#   - Serialize records, based on notion type
#       - This implies we should attach notion schema as class metadata
#       - Maybe I do just take the time to write an auto-generator
#       - It would need to create the class, with setters/getters
#       - Probably maintain a list of fields that have changed, as well (in case we want to add update functionality
#         eventually)


# So, what do I need to do to get the MVP out the door?
# Basically, replicate the existing .js functionality, in better Python. So:
#   - Create `db2py.py`, that parses a Notion schema and creates a Python class with serializing/deserializing
#   - Create classes for the two notion dbs I care about
#   - Test that the classes work (e.g. I can query and create records)
#   - Add logic to:
#       - get_last_execution_time_utc
#       - get_completed_recurring_tasks
#       - create_new_recurring_tasks
#       - save_new_execution
#   - Create a GitHub workflow to execute the Python script
# - [ ] Improve Cron functionality - cron, or:
#   - Daily
#   - Weekly (on same day)
#   - Monthly
#   - Yearly
#   - Every (day/weekday)
#   - Every (X) weeks on (monday/tuesday/wednesday/...)
#   - Every (X) months on the (X) day
#   - Every (X) months on the (first/second/third/fourth/fifth/last) (monday/tuesday/wednesday/...)
#   - Every (X) months on the (first/last) workday
#
# Then, we can figure out what's next.
