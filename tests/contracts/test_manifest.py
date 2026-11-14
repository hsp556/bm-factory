from datetime import date, datetime

import pytest
from pydantic import ValidationError

from bmfactory.contracts.command import parse_command
from bmfactory.contracts.job import Job
from bmfactory.contracts.manifest import Manifest, safe_relative_path

RUN = "CAP-FY2526-LIB-20261114-01"
SHA = "a" * 64


def good_manifest() -> dict:
    cmd = parse_command("CAP | FY 2025-26 | Industry: software development | Product: SaaS", date(2026, 11, 14))
    return {
        "schema_version": "1.0",
        "run_id": RUN,
        "command": cmd.model_dump(),
        "source": {"database": "Capitaline", "data_date": "2026-11-10", "year_codes": ["202603", "202503", "202403"]},
        "layers": [{"id": "L1", "field": "NICCode", "sql": "NICCode IN ('6201')", "row_count": 120}],
        "universe": {"distinct_companies": 120, "peer_set": None},
        "files": [
            {
                "path": f"02-Raw-Dumps/{RUN}_L1_NICCode_001.csv",
                "kind": "raw_dump",
                "layer": "L1",
                "sha256": SHA,
                "bytes": 2048,
                "sharepoint_url": None,
            }
        ],
        "status": "complete",
        "fallbacks_used": [],
        "human_touches": 0,
    }


def test_good_manifest_valid():
    Manifest.model_validate(good_manifest())


@pytest.mark.parametrize(
    "p",
    [
        "../x.csv",
        "/etc/x",
        "C:\\x.csv",
        "02-Raw-Dumps/../../x",
        "02-Raw-Dumps/CON",
        "02-Raw-Dumps/nul.csv",
        "Random/x.csv",
        "02-Raw-Dumps/a|b.csv",
        "",
        "\\\\server\\share\\x.csv",
        "D:x.csv",
        "02-Raw-Dumps//x.csv",
        "02-Raw-Dumps/./x.csv",
        "02-Raw-Dumps/com1.txt",
        "02-Raw-Dumps/x.csv\n",
        "02-Raw-Dumps/x\x00.csv",
        "02-Raw-Dumps/CON .csv",
        "02-Raw-Dumps/x.csv.",
        "02-Raw-Dumps",
    ],
)
def test_unsafe_paths_rejected(p):
    with pytest.raises(ValueError):
        safe_relative_path(p)


def test_backslashes_normalised():
    assert safe_relative_path("99-Logs\\run-record.json") == "99-Logs/run-record.json"


def test_file_entry_path_stored_normalised():
    m = good_manifest()
    m["files"][0]["path"] = m["files"][0]["path"].replace("/", "\\")
    assert Manifest.model_validate(m).files[0].path == f"02-Raw-Dumps/{RUN}_L1_NICCode_001.csv"


def test_unsafe_file_entry_path_rejected():
    m = good_manifest()
    m["files"][0] = {**m["files"][0], "path": "../x.csv", "kind": "log", "layer": None}
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_raw_dump_name_must_match_run_and_layer():
    m = good_manifest()
    m["files"][0]["layer"] = "L2"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)
    m = good_manifest()
    m["files"][0]["path"] = "02-Raw-Dumps/OTHER_L1_NICCode_001.csv"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


@pytest.mark.parametrize(
    "name",
    [
        f"{RUN}_L9_NICCode_001.csv",
        f"{RUN}_L1_NICCode_01.csv",
        f"{RUN}_L1_NIC-Code_001.csv",
        f"{RUN}_L1_NICCode_001.txt",
        f"{RUN}_L1_NICCode_\u0661\u0662\u0663.csv",
        "CAP-FY2526-LIB-20261114x01_L1_NICCode_001.csv",
    ],
)
def test_bad_raw_dump_names_rejected(name):
    m = good_manifest()
    m["files"][0]["path"] = f"02-Raw-Dumps/{name}"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_raw_dump_must_be_in_raw_dumps_folder():
    m = good_manifest()
    m["files"][0]["path"] = f"06-Workings/{RUN}_L1_NICCode_001.csv"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_duplicate_paths_rejected():
    m = good_manifest()
    m["files"].append(dict(m["files"][0]))
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_duplicate_paths_after_normalisation_rejected():
    m = good_manifest()
    dup = dict(m["files"][0])
    dup["path"] = dup["path"].replace("/", "\\")
    m["files"].append(dup)
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


@pytest.mark.parametrize("sha", ["XYZ", "A" * 64, "a" * 63, "a" * 64 + "\n"])
def test_bad_sha_rejected(sha):
    m = good_manifest()
    m["files"][0]["sha256"] = sha
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_bad_manifest_run_id_rejected():
    m = good_manifest()
    m["run_id"] = "bad"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [("files", "bytes", -1), ("layers", "row_count", -1), ("layers", "id", "L9")],
)
def test_bad_numbers_and_layer_ids_rejected(section, key, value):
    m = good_manifest()
    m[section][0][key] = value
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_negative_human_touches_rejected():
    m = good_manifest()
    m["human_touches"] = -1
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_job_rejects_bad_run_id():
    cmd = parse_command("CAP | Industry: x | Product: y", date(2026, 11, 14))
    with pytest.raises(ValidationError):
        Job(run_id="bad", dest="x", command=cmd, created_at=datetime(2026, 11, 14), status="inbox")


def test_job_round_trips_from_json():
    cmd = parse_command("CAP | Industry: x | Product: y", date(2026, 11, 14))
    job = Job(run_id=RUN, dest="BM Backup/Capitaline", command=cmd, created_at=datetime(2026, 11, 14), status="inbox")
    assert Job.model_validate_json(job.model_dump_json()) == job
