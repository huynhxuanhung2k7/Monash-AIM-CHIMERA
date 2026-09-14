"""Shared strict contract primitives for Task 1."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

SCHEMA_VERSION_V1: Literal["1.0"] = "1.0"

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    ),
]
Sha256Digest = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$"),
]


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        str_strip_whitespace=True,
        validate_default=True,
    )


def ensure_unique(values: tuple[object, ...], *, field_name: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field_name} must not contain duplicates")
