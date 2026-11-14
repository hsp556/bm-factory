"""A queue ticket for one run, loaded from JSON written by the Command Centre (untrusted)."""

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from bmfactory.contracts.command import Command
from bmfactory.contracts.ids import check_run_id_matches, parse_run_id
from bmfactory.contracts.manifest import safe_segments


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    dest: str  # a relative SharePoint folder path, e.g. "BM Backup/Capitaline"
    command: Command
    created_at: AwareDatetime
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

    @model_validator(mode="after")
    def _run_id_matches_command(self) -> "Job":
        check_run_id_matches(self.run_id, self.command.db, self.command.fy)
        return self
