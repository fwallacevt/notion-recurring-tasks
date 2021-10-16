"""Utilitizes for manipulating names of model classes and tables."""

import re

# Singular forms of words that appear in table names, but that can't be
# predicted from simple grammatical rules.
_IRREGULAR_SINGULARS = {
    "fpd_batches": "fpd_batch",
    "loose_matches": "loose_match",
    "points_of_interest": "point_of_interest",
    "rolodexes": "rolodex",
}


def singularize(s: str) -> str:
    """Convert a plural word to a singlular one. This mirrors a common Rails
    function whose job is to convert plural table names into singular class
    names. E.g. "deliveries" to "delivery".

    Just add special cases here as needed."""
    if s in _IRREGULAR_SINGULARS:
        return _IRREGULAR_SINGULARS[s]
    return re.sub("s$", "", re.sub("ies$", "y", s))


def enum_name_to_alias(name: str) -> str:
    """Convert names like "To do" to "TO_DO"."""
    return name.replace(" ", "_").upper()


def property_to_enum_class_name(name: str) -> str:
    """Convert names like "Due date" to "DueDate"."""
    # First, convert to snake case, so we can reuse table_to_class_name
    name = name.replace(" ", "_").lower()
    return f"{table_to_class_name(name)}Enum"


def table_to_class_name(name: str) -> str:
    """Convert names like "foo_bars" to "FooBar"."""
    name = singularize(name)
    components = name.split("_")
    components[-1] = singularize(components[-1])
    return "".join(c.capitalize() for c in components)
