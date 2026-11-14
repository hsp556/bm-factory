"""A station's knowledge as data: the step catalogue (WHAT to do, in SOP order) and the screen map (WHERE each
named control is). When the vendor changes the UI, only the screen map changes.

Both files are YAML that a learning run may rewrite, so they are untrusted: loaded with `yaml.safe_load` only
and held to the models below.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from bmfactory.contracts.command import _Text
from bmfactory.contracts.ids import DB_CODES

_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"
_NAME_MAX = 64
_STEPS_MAX = 500
_TARGETS_MAX = 500
_PARAMS_MAX = 20
_PATH_MAX = 20

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


def _load_mapping(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level, got {type(data).__name__}")
    return data


def load_steps(path: Path) -> StepCatalogue:
    return StepCatalogue.model_validate(_load_mapping(path))


def load_screen_map(path: Path) -> ScreenMap:
    return ScreenMap.model_validate(_load_mapping(path))


def missing_targets(steps: StepCatalogue, smap: ScreenMap) -> list[str]:
    """Targets the steps use that the screen map does not define (sorted, unique). Reported, never raised."""
    return sorted({s.target for s in steps.steps if s.target is not None and s.target not in smap.targets})
