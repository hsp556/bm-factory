"""A station's knowledge as data: the step catalogue (WHAT to do, in SOP order) and the screen map (WHERE each
named control is). When the vendor changes the UI, only the screen map changes.

Both files are YAML that a learning run may rewrite, so they are untrusted: capped at 256 KiB, parsed with a
SafeLoader subclass that also rejects duplicate keys, and held to the models below.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator, model_validator

from bmfactory.contracts.command import _Text
from bmfactory.contracts.ids import DB_CODES

_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
_NAME_MAX = 64
_STEPS_MAX = 500
_TARGETS_MAX = 500
_PARAMS_MAX = 20
_PATH_MAX = 20
_FILE_MAX = 256 * 1024  # checked before parsing, so an alias bomb or huge file never reaches the YAML parser

_Name = Annotated[str, StringConstraints(pattern=_NAME_PATTERN, max_length=_NAME_MAX)]
_Version = Annotated[int, Field(ge=1, strict=True)]
_Strict = ConfigDict(extra="forbid")


def _known_db(v: str) -> str:
    if v not in DB_CODES:
        raise ValueError(f"unknown database code {v[:10]!r}; expected one of {', '.join(DB_CODES)}")
    return v


class StepDef(BaseModel):
    model_config = _Strict

    id: _Name
    gate: Literal["G1", "G2", "G3"]
    action: Literal["click", "select", "type", "read_text", "read_grid", "screenshot", "wait_for"]
    target: _Name | None
    params: Annotated[dict[_Name, _Text], Field(max_length=_PARAMS_MAX)] = {}
    sop_ref: _Text

    @model_validator(mode="after")
    def _target_needed(self) -> "StepDef":
        if self.target is None and self.action != "screenshot":
            raise ValueError(f"target: required for action {self.action!r}")
        return self


class StepCatalogue(BaseModel):
    model_config = _Strict

    database: str
    version: _Version
    steps: list[StepDef] = Field(max_length=_STEPS_MAX)

    _db = field_validator("database")(_known_db)

    @model_validator(mode="after")
    def _unique_ids(self) -> "StepCatalogue":
        seen: set[str] = set()
        for s in self.steps:
            if s.id in seen:
                raise ValueError(f"steps: duplicate step id {s.id!r}")
            seen.add(s.id)
        return self


class Locator(BaseModel):
    model_config = _Strict

    backend: Literal["uia", "win32", "playwright"]
    window: _Text
    control_type: _Text | None
    auto_id: _Text | None
    name: _Text | None
    path: list[_Text] = Field(default=[], max_length=_PATH_MAX)

    @model_validator(mode="after")
    def _has_identifier(self) -> "Locator":
        if self.auto_id is None and self.name is None and not self.path:
            raise ValueError("locator needs at least one of auto_id, name or path")
        return self


class ScreenMap(BaseModel):
    model_config = _Strict

    database: str
    version: _Version
    verified: Annotated[bool, Field(strict=True)]
    app_version_seen: _Text | None
    recorded_at: datetime | None
    targets: Annotated[dict[_Name, Locator], Field(max_length=_TARGETS_MAX)]

    _db = field_validator("database")(_known_db)


_M = TypeVar("_M", StepCatalogue, ScreenMap)


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys, so a rewrite cannot silently shadow an entry."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in seen
        except TypeError:  # unhashable key: construct_mapping below reports it
            continue
        if duplicate:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def _load(path: Path, model: type[_M]) -> _M:
    """Read a station YAML file (untrusted). Every failure is a ValueError naming the file."""
    if path.stat().st_size > _FILE_MAX:
        raise ValueError(f"{path}: file is larger than {_FILE_MAX // 1024} KiB")
    with path.open("rb") as f:
        raw = f.read(_FILE_MAX + 1)
    if len(raw) > _FILE_MAX:  # grew after the size check
        raise ValueError(f"{path}: file is larger than {_FILE_MAX // 1024} KiB")
    try:
        data = yaml.load(raw.decode("utf-8"), Loader=_UniqueKeyLoader)
    except (UnicodeDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"{path}: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level, got {type(data).__name__}")
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ValueError(f"{path}: {e}") from e


def load_steps(path: Path) -> StepCatalogue:
    return _load(path, StepCatalogue)


def load_screen_map(path: Path) -> ScreenMap:
    return _load(path, ScreenMap)


def missing_targets(steps: StepCatalogue, smap: ScreenMap) -> list[str]:
    """Targets the steps use that the screen map does not define (sorted, unique). Reported, never raised."""
    return sorted({s.target for s in steps.steps if s.target is not None and s.target not in smap.targets})
