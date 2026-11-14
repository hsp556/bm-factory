"""A queue ticket for one run, loaded from JSON written by the Command Centre (untrusted)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from bmfactory.contracts.command import Command, _Text
from bmfactory.contracts.ids import parse_run_id


class Job(BaseModel):
    run_id: str
    dest: _Text
    command: Command
    created_at: datetime
    status: Literal["inbox", "running", "enable", "stuck", "done"]

    @field_validator("run_id")
    @classmethod
    def _valid_run_id(cls, v: str) -> str:
        parse_run_id(v)
        return v
