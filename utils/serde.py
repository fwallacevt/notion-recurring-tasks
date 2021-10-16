"""Utilities for working with JSON"""

from abc import ABCMeta
from copy import copy
from typing import (
    Any,
    Callable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from uuid import UUID

# from .locator import Locator

D = TypeVar("D", bound="Deserializable")


class Deserializable(metaclass=ABCMeta):
    """A value which can be deserialized from JSON."""

    @classmethod
    def from_json(cls: Type[D], json: Any) -> D:
        """Parse and validate a message of this type from a JSON value.

        This is not expected to be particularly fast, merely convenient."""

        # Make a shallow copy of our object so that we can mutate it in place
        # without any surprises.
        if not isinstance(json, dict):
            raise Exception(f"expected dict, got JSON value {json}")
        json = copy(json)
        annotations = recursively_get_annotations(cls)
        for key in json:
            # Look up the declared type of this member variable.
            if not key in annotations:
                raise Exception(
                    f"cannot deserialize {json}: {key} not declared in {cls}",
                )

            original_ty = annotations[key]
            base_ty, args = _degenericize_type(original_ty)
            # Convert `Optional[T]` to `T`. `Optional[T]` just becomes `Union[T, NoneType]`, so
            # we need to undo that.
            # See https://stackoverflow.com/q/45957615/12089 for more info.
            if (
                base_ty == Union
                and args is not None
                and len(args) == 2
                and args[1] == None.__class__
            ):
                ty = args[0]
            else:
                ty = original_ty

            json[key] = recursively_deserialize_type(ty, value=json[key])

        # Let `__init__` handle defaulting, assignments, etc. But we need to
        # cast it to a generic `Callable` so `mypy` doesn't complain.
        cls_untyped: Callable = cls
        return cls_untyped(**json)


class Serializable(metaclass=ABCMeta):
    """A value which can be serialized to JSON."""

    def to_json(self) -> Mapping[str, Any]:
        """Serialize this type as a JSON-compatible Python structure.

        This is not expected to be particularly fast, merely convenient."""

        # Make a shallow copy of our result to avoid modifying the underlying
        # object.
        result = copy(vars(self))

        # Serialize any children that implement `Serializable`.
        annotations = recursively_get_annotations(self.__class__)
        for key in result:
            assert key in annotations

            original_ty = annotations[key]
            base_ty, args = _degenericize_type(original_ty)
            # Convert `Optional[T]` to `T`. `Optional[T]` just becomes `Union[T, NoneType]`, so
            # we need to undo that.
            # See https://stackoverflow.com/q/45957615/12089 for more info.
            if (
                base_ty == Union
                and args is not None
                and len(args) == 2
                and args[1] == None.__class__
            ):
                ty = args[0]
            else:
                ty = original_ty

            result[key] = recursively_serialize_type(ty, value=result[key])

        return result


def recursively_get_annotations(ty: Type) -> Mapping[str, Type]:
    """Given a type, recursively gather annotations for its subclasses as well. We only
    gather annotations if its subclasses are themselves subclasses of Deserializable,
    and not Deserializable itself.

    This is bad evil code that uses internal Python details that may break in
    3.8 or later."""
    # Get initial annotations
    annotations: Mapping[str, Type] = getattr(ty, "__annotations__", {})

    # Recursively gather annotations for base classes
    for base in getattr(ty, "__bases__", {}):
        if issubclass(base, Deserializable) and (base != Deserializable):
            annotations = dict(
                annotations, **recursively_get_annotations(base)
            )

    return annotations


def recursively_deserialize_type(ty: Type, value: Optional[Any] = None) -> Any:
    """Deserialize the member variable if appropriate."""
    # If type is generic, degenericize it
    ty, args = _degenericize_type(ty)

    if value is None:
        # If value is None, we know None always deserializes to None
        return
    elif ty == UUID:
        return UUID(value)
    # elif ty == Locator:
    #     return Locator(value)
    elif ty == dict:
        if args == [str, Any]:
            return value
        else:
            raise Exception(f"Can't deserialize dict type: {str(args)}")
    elif ty == list:
        if args is None or len(args) != 1:
            raise Exception(f"Can't deserialize list, args: {str(args)}")
        return [
            recursively_deserialize_type(ty=args[0], value=v) for v in value
        ]
    elif ty != Any and issubclass(ty, Deserializable):
        return ty.from_json(value)

    return value


def recursively_serialize_type(
    ty: Type,
    value: Optional[Any] = None,
) -> Any:
    """Serialize the member variable if possible."""
    # If type is generic, degenericize it
    ty, args = _degenericize_type(ty)

    if value is None:
        return
    elif ty == UUID:
        return str(value)
    # elif ty == Locator:
    #     return str(value)
    elif ty == dict:
        if args == [str, Any]:
            return value
        else:
            raise Exception(f"Unknown dict args: {str(args)}")
    elif ty == list:
        if args is None or len(args) == 0:
            raise Exception(f"List must have type")
        return [recursively_serialize_type(ty=args[0], value=v) for v in value]
    # Have to check this here because Any is not a class, and therefore does not have `issubclass` method. If we don't
    # check this, we get an error: `TypeError: issubclass() arg 1 must be a class`
    elif ty != Any and issubclass(ty, Serializable):
        return value.to_json()

    return value


def _degenericize_type(ty: Type) -> Tuple[Any, Optional[List[Type]]]:
    """Given a type, determine if it is an instantiation of a generic type, and
    if so, return the underlying type and the argument types used to instantiate
    it. Otherwise just return the input type.

    This is bad evil code that uses internal Python details that may break in
    3.8 or later."""
    if hasattr(ty, "__origin__") and hasattr(ty, "__args__"):
        return (getattr(ty, "__origin__"), list(ty.__args__))
    else:
        return (ty, None)
