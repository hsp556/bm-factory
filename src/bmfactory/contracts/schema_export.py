"""Write the JSON Schemas of the data contracts, deterministically, for other programs to validate against."""

import json
from pathlib import Path

from bmfactory.contracts.command import Command
from bmfactory.contracts.job import Job
from bmfactory.contracts.manifest import Manifest

_MODELS = {"command": Command, "job": Job, "manifest": Manifest}


def export_schemas(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, model in _MODELS.items():
        path = out_dir / f"{name}.schema.json"
        text = json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n"
        with path.open("w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        paths.append(path)
    return paths
