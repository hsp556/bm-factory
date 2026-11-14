"""A queue ticket for one run, loaded from JSON written by the Command Centre (untrusted)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from bmfactory.contracts.command import Command
from bmfactory.contracts.ids import parse_run_id
from bmfactory.contracts.manifest import safe_segments


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    dest: str  # a relative SharePoint folder path, e.g. "BM Backup/Capitaline"
    command: Command
    created_at: datetime
    status: Literal["inbox", "running", "enable", "stuck", "done"]

    @field_validator("run_id")
    @classmethod
    def _valid_run_id(cls, v: str) -> str:
        parse_run_id(v)
        return v

    @field_validator("dest")
    @classmethod
    def _relative_folder(cls, v: str) -> str:
        return "/".join(safe_segments(v))
