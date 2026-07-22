from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]


def load_verifier():
    path = REPO / "scripts" / "verify_reproducibility.py"
    spec = importlib.util.spec_from_file_location("verify_reproducibility", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_manifest(root: Path, rows: list[dict[str, str]]) -> Path:
    path = root / "PUBLIC_RELEASE_SHA256.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("relative_path", "sha256", "size_bytes"),
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def manifest_row(path: Path, relative: str) -> dict[str, str]:
    return {
        "relative_path": relative,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": str(path.stat().st_size),
    }


def copy_science_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "science"
    (root / "manuscript").mkdir(parents=True)
    (root / "reports").mkdir()
    (root / "data_manifest").mkdir()
    shutil.copy2(REPO / "manuscript" / "MANUSCRIPT.md", root / "manuscript" / "MANUSCRIPT.md")
    shutil.copytree(REPO / "manuscript" / "tables", root / "manuscript" / "tables")
    shutil.copy2(
        REPO / "reports" / "constructive_benchmark.json",
        root / "reports" / "constructive_benchmark.json",
    )
    shutil.copy2(
        REPO / "data_manifest" / "allen_assets.csv",
        root / "data_manifest" / "allen_assets.csv",
    )
    return root


def test_numerical_claims_and_allen_assets_are_consistent() -> None:
    verifier = load_verifier()
    checks, _ = verifier.scientific_checks(REPO)
    assert len(checks) == 25
    assert all(check.passed for check in checks)
    assert verifier.validate_allen_assets(REPO) == 40


def test_public_case_metadata_and_eligibility_schema_are_canonical() -> None:
    with (REPO / "manuscript/tables/supplementary_table_all_72_cases.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        cases = list(csv.DictReader(handle))
    with (REPO / "manuscript/tables/supplementary_table_all_216_metric_states.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        states = list(csv.DictReader(handle))
    assert len({row["case_number"] for row in cases}) == 72
    assert {row["model_dt_s"] for row in cases} == {"0.00005", "0.000005", "0.000025"}
    assert all(row["recording_selection"] for row in cases + states)
    assert len({(row["case_number"], row["metric"]) for row in states}) == 216
    assert {row["status"] for row in states} == {"calculated", "non_evaluable"}
    assert {row["non_evaluable_reason"] for row in states} == {
        "",
        "no_in_window_spike",
        "not_applicable_to_protocol",
        "insufficient_coverage",
    }


def test_public_json_is_rfc8259_strict_sorted_and_stable() -> None:
    for path in (REPO / ".zenodo.json", REPO / "reports/constructive_benchmark.json"):
        text = path.read_text(encoding="utf-8")

        def reject_constant(value: str) -> None:
            raise ValueError(f"non-standard JSON constant: {value}")

        parsed = json.loads(text, parse_constant=reject_constant)
        assert text == json.dumps(parsed, allow_nan=False, indent=2, sort_keys=True) + "\n"


def test_supplementary_figure_s1_uses_accessible_cell_text_and_portable_fonts() -> None:
    path = REPO / "manuscript/figures/supplementary_figure_s1_outcome_eligibility_matrix.svg"
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    children = list(root)
    navy_rectangles = 0
    for index, node in enumerate(children):
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "text":
            assert node.attrib["font-family"] == "Arial, sans-serif"
        if tag == "rect" and node.attrib.get("fill") == "#1F4E79":
            navy_rectangles += 1
            following = children[index + 1]
            assert following.tag.rsplit("}", 1)[-1] == "text"
            assert following.attrib.get("fill") == "#FFFFFF"
    assert navy_rectangles == 123
    description = next(node for node in children if node.tag.rsplit("}", 1)[-1] == "desc")
    assert "72-row by three-column matrix" in (description.text or "")


def test_science_only_default_is_read_only() -> None:
    verifier = load_verifier()
    before = {
        path.relative_to(REPO).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in REPO.rglob("*")
        if path.is_file()
    }
    assert verifier.main(["--root", str(REPO), "--science-only"]) == 0
    after = {
        path.relative_to(REPO).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in REPO.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_optional_report_writes_only_requested_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    output = tmp_path / "report.md"
    assert verifier.main(["--root", str(REPO), "--science-only", "--report", str(output)]) == 0
    assert output.read_text(encoding="utf-8").startswith("# Numerical consistency")
    assert {path for path in tmp_path.rglob("*") if path.is_file()} == {output}


def test_release_manifest_accepts_untampered_inventory(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = tmp_path / "payload.txt"
    payload.write_text("stable\n", encoding="utf-8")
    manifest = write_manifest(tmp_path, [manifest_row(payload, "payload.txt")])
    assert verifier.verify_release_manifest(tmp_path, manifest) == 1


def test_release_manifest_ignores_git_metadata(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = tmp_path / "payload.txt"
    payload.write_text("stable\n", encoding="utf-8")
    manifest = write_manifest(tmp_path, [manifest_row(payload, "payload.txt")])
    git_head = tmp_path / ".git" / "HEAD"
    git_head.parent.mkdir()
    git_head.write_text("ref: refs/heads/main\n", encoding="utf-8")
    assert verifier.verify_release_manifest(tmp_path, manifest) == 1


def test_release_manifest_names_tampered_file(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = tmp_path / "payload.txt"
    payload.write_text("stable\n", encoding="utf-8")
    manifest = write_manifest(tmp_path, [manifest_row(payload, "payload.txt")])
    payload.write_text("staple\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch: payload.txt"):
        verifier.verify_release_manifest(tmp_path, manifest)


@pytest.mark.parametrize(
    "relative",
    ["../outside.txt", "/absolute.txt", "C:/absolute.txt", "folder\\file.txt"],
)
def test_release_manifest_rejects_unsafe_paths(tmp_path: Path, relative: str) -> None:
    verifier = load_verifier()
    manifest = write_manifest(
        tmp_path,
        [{"relative_path": relative, "sha256": "0" * 64, "size_bytes": "0"}],
    )
    with pytest.raises(ValueError, match="Unsafe or duplicate manifest path"):
        verifier.verify_release_manifest(tmp_path, manifest)


def test_release_manifest_rejects_duplicate_and_missing_paths(tmp_path: Path) -> None:
    verifier = load_verifier()
    payload = tmp_path / "payload.txt"
    payload.write_text("stable\n", encoding="utf-8")
    row = manifest_row(payload, "payload.txt")
    duplicate = write_manifest(tmp_path, [row, row])
    with pytest.raises(ValueError, match="Unsafe or duplicate manifest path"):
        verifier.verify_release_manifest(tmp_path, duplicate)
    missing = write_manifest(
        tmp_path,
        [{"relative_path": "missing.txt", "sha256": "0" * 64, "size_bytes": "0"}],
    )
    with pytest.raises(ValueError, match="Manifest file missing: missing.txt"):
        verifier.verify_release_manifest(tmp_path, missing)


def test_altered_scientific_total_fails_named_check(tmp_path: Path) -> None:
    verifier = load_verifier()
    root = copy_science_fixture(tmp_path)
    path = root / "manuscript" / "tables" / "supplementary_table_all_72_cases.csv"
    rows = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
    checks, _ = verifier.scientific_checks(root)
    failed = {check.name for check in checks if not check.passed}
    assert "72 analysis cases" in failed


def test_malformed_benchmark_json_fails_explicitly(tmp_path: Path) -> None:
    verifier = load_verifier()
    root = copy_science_fixture(tmp_path)
    (root / "reports" / "constructive_benchmark.json").write_text("{", encoding="utf-8")
    with pytest.raises(Exception, match="Expecting property name"):
        verifier.scientific_checks(root)


def test_missing_allen_manifest_column_fails_explicitly(tmp_path: Path) -> None:
    verifier = load_verifier()
    root = tmp_path / "assets"
    (root / "data_manifest").mkdir(parents=True)
    (root / "data_manifest" / "allen_assets.csv").write_text(
        "asset_class,specimen_ids\nsource_recording,314822529\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing columns"):
        verifier.validate_allen_assets(root)
