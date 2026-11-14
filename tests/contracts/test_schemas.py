import json
from pathlib import Path

from bmfactory.contracts.schema_export import export_schemas

COMMITTED = Path(__file__).resolve().parents[2] / "contracts" / "schemas"
NAMES = ["command.schema.json", "job.schema.json", "manifest.schema.json"]


def test_export_writes_three_schemas(tmp_path):
    paths = export_schemas(tmp_path)
    assert sorted(p.name for p in paths) == NAMES
    for p in paths:
        assert p.is_file()
        assert json.loads(p.read_text(encoding="utf-8"))["title"]


def test_committed_schemas_match_models(tmp_path):
    export_schemas(tmp_path)
    for name in NAMES:
        assert (tmp_path / name).read_bytes() == (COMMITTED / name).read_bytes(), f"{name} is stale; re-run export_schemas"
