from datetime import date, datetime

import pytest
from pydantic import ValidationError

from bmfactory.contracts.command import parse_command
from bmfactory.contracts.job import Job
from bmfactory.contracts.manifest import FileEntry, Manifest, safe_relative_path

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
                "time": "2026-11-14T10:00:00+05:30",
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


# --- fix round 1 ---------------------------------------------------------------------------------

def _cmd():
    return parse_command("CAP | Industry: x | Product: y", date(2026, 11, 14))


def _job(**over):
    kw = dict(run_id=RUN, dest="BM Backup/Capitaline", command=_cmd(), created_at=datetime(2026, 11, 14), status="inbox")
    kw.update(over)
    return Job.model_validate(kw)


def _file(**over) -> dict:
    return {**good_manifest()["files"][0], **over}


# F1
def test_file_time_required():
    m = good_manifest()
    del m["files"][0]["time"]
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_naive_file_time_rejected():
    m = good_manifest()
    m["files"][0]["time"] = "2026-11-14T10:00:00"
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


# F2
@pytest.mark.parametrize(
    "dest",
    ["../../Other Client", "C:\\x", "\\host\\share", "https://evil/", "", "/BM Backup", "BM Backup//x",
     "BM Backup/./x", "BM Backup/x.", "BM Backup/x ", "BM Backup/a|b", "BM Backup/x\n", "a" * 401],
)
def test_bad_dest_rejected(dest):
    with pytest.raises(ValidationError):
        _job(dest=dest)


@pytest.mark.parametrize("dest", ["BM Backup/Capitaline", "BM Backup\\Capitaline"])
def test_good_dest_accepted_and_normalised(dest):
    assert _job(dest=dest).dest == "BM Backup/Capitaline"


# F3
@pytest.mark.parametrize(
    "url",
    ["http://x.sharepoint.com/a", "javascript:alert(1)", "https://evil.example/a", "https://sharepoint.com.evil.example/a",
     "https://user:pw@x.sharepoint.com/a", "https://x.sharepoint.com/a\n", "https://x.sharepoint.com/" + "a" * 2000],
)
def test_bad_sharepoint_url_rejected(url):
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(sharepoint_url=url))


@pytest.mark.parametrize("url", ["https://contoso.sharepoint.com/sites/x/a.csv", "https://Contoso.SharePoint.com/sites/x/a.csv"])
def test_good_sharepoint_url_accepted(url):
    assert FileEntry.model_validate(_file(sharepoint_url=url)).sharepoint_url == url


# A1
def test_duplicate_paths_case_insensitive():
    m = good_manifest()
    log = {**m["files"][0], "kind": "log", "layer": None}
    m["files"] += [{**log, "path": "99-Logs/A.json"}, {**log, "path": "99-Logs/a.json"}]
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


# A2
def test_unknown_keys_rejected():
    m = good_manifest()
    m["extra"] = 1
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(extra=1))
    with pytest.raises(ValidationError):
        _job(extra=1)


# A3
def test_non_raw_dump_in_raw_dumps_folder_rejected():
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(path="02-Raw-Dumps/notes.csv", kind="working", layer=None))


def test_counts_json_in_raw_dumps_folder_accepted_as_working():
    FileEntry.model_validate(_file(path="02-Raw-Dumps/counts.json", kind="working", layer=None))
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(path="02-Raw-Dumps/counts.json", kind="log", layer=None))


def test_raw_dump_outside_raw_dumps_folder_rejected_on_file_entry():
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(path=f"06-Workings/{RUN}_L1_NICCode_001.csv"))


# A4
@pytest.mark.parametrize("layer", ["L0", "L9", "x", ""])
def test_layer_must_be_l1_to_l8(layer):
    with pytest.raises(ValidationError):
        FileEntry.model_validate(_file(path="06-Workings/w.csv", kind="working", layer=layer))


# A5
def test_layer_ids_unique_and_capped():
    m = good_manifest()
    m["layers"].append(dict(m["layers"][0]))
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)
    m = good_manifest()
    m["layers"] = [{**m["layers"][0], "id": f"L{i % 8 + 1}"} for i in range(9)]
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_files_capped():
    m = good_manifest()
    log = {**m["files"][0], "kind": "log", "layer": None}
    m["files"] = [{**log, "path": f"99-Logs/{i}.json"} for i in range(5001)]
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_fallbacks_capped_and_printable():
    m = good_manifest()
    m["fallbacks_used"] = ["vision"] * 101
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)
    m = good_manifest()
    m["fallbacks_used"] = ["vision\x1b[31m"]
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [("layers", "field", ""), ("layers", "field", "x" * 201), ("layers", "field", "a\nb"),
     ("source", "database", "Cap\u202eitaline"), ("universe", "peer_set", "x" * 201),
     ("layers", "sql", "x" * 20001), ("layers", "sql", "a\x00b")],
)
def test_text_fields_bounded(section, key, value):
    m = good_manifest()
    target = m[section][0] if isinstance(m[section], list) else m[section]
    target[key] = value
    with pytest.raises(ValidationError):
        Manifest.model_validate(m)


def test_sql_allows_whitespace_controls():
    m = good_manifest()
    m["layers"][0]["sql"] = "NICCode IN ('6201')\r\n\tAND x = 1"
    Manifest.model_validate(m)


def test_path_length_capped():
    with pytest.raises(ValueError):
        safe_relative_path("06-Workings/" + "a" * 389)
    assert safe_relative_path("06-Workings/" + "a" * 388)


# A6
@pytest.mark.parametrize("p", ["02-Raw-Dumps/CONSOLE.csv", "06-Workings/COM10.csv", "06-Workings/a.b.csv"])
def test_reserved_check_does_not_over_reject(p):
    assert safe_relative_path(p) == p


@pytest.mark.parametrize("stem", ["COM\u00b9", "COM\u00b2", "COM\u00b3", "LPT\u00b9", "LPT\u00b2", "LPT\u00b3", "CONIN$", "conout$"])
def test_extra_reserved_stems_rejected(stem):
    with pytest.raises(ValueError):
        safe_relative_path(f"06-Workings/{stem}.csv")


# A7
def test_error_echo_truncated():
    with pytest.raises(ValueError) as e:
        safe_relative_path("Random/" + "z" * 300)
    assert "z" * 51 not in str(e.value)
    with pytest.raises(ValidationError) as e:
        _job(dest="BM Backup/" + "z" * 300 + "|")
    assert "z" * 51 not in str(e.value)
