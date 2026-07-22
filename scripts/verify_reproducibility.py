#!/usr/bin/env python3
"""Verify release integrity, Allen asset metadata, and scientific claims."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
ASSET_COUNTS = {
    "source_recording": 6,
    "glif_configuration": 6,
    "morphology": 6,
    "perisomatic_fit_parameters": 6,
    "mechanism_source": 16,
}
ASSET_FIELDS = {
    "asset_class",
    "specimen_ids",
    "well_known_file_id",
    "filename",
    "source_url",
    "sha256",
}


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    evidence: str


def read_csv(path: Path, required: Iterable[str] = ()) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = set(required) - fields
        if missing:
            raise ValueError(f"{path}: missing columns {sorted(missing)}")
        return list(reader)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_strict_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"{path}: non-standard JSON constant {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def load_outcome_eligibility():
    source_root = str(REPO / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from neuronal_model_replay_validation import outcome_eligibility

    return outcome_eligibility


def validate_allen_assets(root: Path) -> int:
    path = root / "data_manifest" / "allen_assets.csv"
    rows = read_csv(path, ASSET_FIELDS)
    counts = Counter(row["asset_class"] for row in rows)
    if counts != ASSET_COUNTS:
        raise ValueError(f"{path}: unexpected asset counts {dict(counts)}")
    ids: set[str] = set()
    recording_hashes = 0
    for row in rows:
        well_known_file_id = row["well_known_file_id"]
        if not well_known_file_id.isdigit() or well_known_file_id in ids:
            raise ValueError(f"{path}: invalid or duplicate ID {well_known_file_id!r}")
        ids.add(well_known_file_id)
        expected_url = (
            f"https://api.brain-map.org/api/v2/well_known_file_download/{well_known_file_id}"
        )
        if row["source_url"] != expected_url:
            raise ValueError(f"{path}: unexpected URL for {well_known_file_id}")
        if not row["filename"] or not row["specimen_ids"]:
            raise ValueError(f"{path}: incomplete row for {well_known_file_id}")
        digest = row["sha256"]
        if row["asset_class"] == "source_recording":
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(f"{path}: invalid recording digest for {well_known_file_id}")
            recording_hashes += 1
        elif digest:
            raise ValueError(f"{path}: unverified digest supplied for {well_known_file_id}")
    if recording_hashes != 6:
        raise ValueError(f"{path}: expected six recording digests, found {recording_hashes}")
    return len(rows)


def scientific_checks(root: Path) -> tuple[list[Check], dict[str, Any]]:
    manuscript = (root / "manuscript" / "MANUSCRIPT.md").read_text(encoding="utf-8")
    tables = root / "manuscript" / "tables"
    checks: list[Check] = []

    def add(name: str, condition: bool, evidence: str) -> None:
        checks.append(Check(name, bool(condition), evidence))

    cohort = read_csv(
        tables / "table_1_cohort_and_source_animals.csv",
        {"specimen_id", "analytical_stratum"},
    )
    strata = Counter(row["analytical_stratum"] for row in cohort)
    add("six cells", len(cohort) == 6, f"table rows={len(cohort)}")
    add(
        "one method-development and five evaluation specimens",
        strata == {"method_development": 1, "evaluation": 5},
        f"strata={dict(strata)}",
    )

    cases = read_csv(
        tables / "supplementary_table_all_72_cases.csv",
        {
            "case_number",
            "specimen_id",
            "sweep_number",
            "recording_selection",
            "stimulus_label",
            "model_condition",
            "model_dt_s",
            "recorded_stimulus_window_spike_count",
            "model_stimulus_window_spike_count",
            "recording_baseline_coverage",
            "recording_steady_state_coverage",
            "model_baseline_coverage",
            "model_steady_state_coverage",
        },
    )
    selections = {(row["specimen_id"], row["sweep_number"]) for row in cases}
    conditions = {row["model_condition"] for row in cases}
    selection_rows = read_csv(
        tables / "supplementary_table_recording_selections.csv",
        {"specimen_id", "sweep_number", "recording_selection"},
    )
    selection_lookup = {
        (row["specimen_id"], row["sweep_number"]): row["recording_selection"]
        for row in selection_rows
    }
    selection_consistent = len(selection_lookup) == 24 and all(
        row["recording_selection"]
        == selection_lookup.get((row["specimen_id"], row["sweep_number"]))
        for row in cases
    )
    add(
        "24 recording selections",
        len(selections) == 24 and selection_consistent,
        f"unique selections={len(selections)}; cross-table consistent={selection_consistent}",
    )
    add("three simulation conditions", len(conditions) == 3, f"conditions={sorted(conditions)}")
    expected_dt = {
        "glif_stored_grid": "0.00005",
        "glif_recording_grid": "0.000005",
        "perisomatic_recording_grid_playback": "0.000025",
    }
    unique_case_numbers = len({row["case_number"] for row in cases}) == len(cases)
    model_dt_complete = all(
        row["model_dt_s"] == expected_dt.get(row["model_condition"]) for row in cases
    )
    add(
        "72 analysis cases",
        len(cases) == 72 and unique_case_numbers and model_dt_complete,
        f"case rows={len(cases)}; unique={unique_case_numbers}; normalized dt={model_dt_complete}",
    )

    states = read_csv(
        tables / "supplementary_table_all_216_metric_states.csv",
        {
            "case_number",
            "recording_selection",
            "metric",
            "status",
            "non_evaluable_reason",
            "non_evaluable_category",
            "applicability_rule",
        },
    )
    status_counts = Counter(row["status"] for row in states)
    state_keys = {(row["case_number"], row["metric"]) for row in states}
    controlled_reasons = {"", "no_in_window_spike", "not_applicable_to_protocol", "insufficient_coverage"}
    state_schema_valid = (
        len(state_keys) == len(states)
        and all(row["recording_selection"] for row in states)
        and all(row["non_evaluable_reason"] in controlled_reasons for row in states)
    )
    add(
        "216 outcome records",
        len(states) == 216 and state_schema_valid,
        f"rows={len(states)}; unique and controlled={state_schema_valid}",
    )
    add("122 calculated outcomes", status_counts["calculated"] == 122, str(dict(status_counts)))
    cases_by_number = {row["case_number"]: row for row in cases}
    outcome_eligibility = load_outcome_eligibility()
    eligibility_matches = True
    for row in states:
        case = cases_by_number.get(row["case_number"])
        if case is None:
            eligibility_matches = False
            break
        coverage = tuple(
            float(case[name])
            for name in (
                "recording_baseline_coverage",
                "recording_steady_state_coverage",
                "model_baseline_coverage",
                "model_steady_state_coverage",
            )
            if case[name]
        )
        expected = outcome_eligibility(
            row["metric"],
            recording_spike_count=int(case["recorded_stimulus_window_spike_count"]),
            model_spike_count=int(case["model_stimulus_window_spike_count"]),
            protocol=case["stimulus_label"],
            coverage_values=coverage,
        )
        actual = {key: row[key] for key in expected}
        if actual != expected:
            eligibility_matches = False
            break
    add(
        "94 non-evaluable outcomes",
        status_counts["non_evaluable"] == 94 and eligibility_matches,
        f"statuses={dict(status_counts)}; exact public contract={eligibility_matches}",
    )

    waveform_columns = {
        "exact_boundary",
        "one_source_sample_offset",
        "midpoint_between_solver_steps",
        "sub_solver_step_pulse",
        "consecutive_transitions",
    }
    benchmark = read_csv(
        tables / "table_3_delivered_current_benchmark.csv",
        waveform_columns | {"all_five_criteria_met"},
    )
    add("five original playback methods", len(benchmark) == 5, f"rows={len(benchmark)}")
    add("five benchmark waveforms", bool(benchmark), str(sorted(waveform_columns)))
    add(
        "no original method met all five criteria",
        all(row["all_five_criteria_met"].casefold() == "false" for row in benchmark),
        f"all-five values={[row['all_five_criteria_met'] for row in benchmark]}",
    )

    equilibration_cases = read_csv(
        tables / "supplementary_table_equilibration_case_results.csv",
        {"material_change_criterion_met", "original_period_stability", "extended_period_converged"},
    )
    equilibration_cells = read_csv(
        tables / "table_4_equilibration_cell_findings.csv",
        {"material_change_criterion_met_cases"},
    )
    change_count = sum(
        row["material_change_criterion_met"].casefold() == "true" for row in equilibration_cases
    )
    drift_count = sum(row["original_period_stability"] == "drifting" for row in equilibration_cases)
    convergence_count = sum(
        row["extended_period_converged"].casefold() == "true" for row in equilibration_cases
    )
    per_cell_change = [
        int(row["material_change_criterion_met_cases"]) for row in equilibration_cells
    ]
    add(
        "24 initialization cases",
        len(equilibration_cases) == 24,
        f"rows={len(equilibration_cases)}",
    )
    add("all 24 original periods drifted", drift_count == 24, f"drifting={drift_count}")
    add(
        "all 24 extended periods converged",
        convergence_count == 24,
        f"converged={convergence_count}",
    )
    add(
        "20 cases met a material-change criterion",
        change_count == 20,
        f"criterion met={change_count}",
    )
    add(
        "all six cells had at least three affected selections",
        len(per_cell_change) == 6 and min(per_cell_change) >= 3,
        str(per_cell_change),
    )

    report_path = root / "reports" / "constructive_benchmark.json"
    report = read_strict_json(report_path)
    required_report_fields = {"schema_version", "summaries", "results", "criteria", "software"}
    missing_report_fields = required_report_fields - set(report)
    if missing_report_fields:
        raise ValueError(f"{report_path}: missing fields {sorted(missing_report_fields)}")
    if not isinstance(report["summaries"], list) or not isinstance(report["results"], list):
        raise ValueError(f"{report_path}: summaries and results must be arrays")
    lookup = {
        (row["current_playback_method"], row["solver_dt_ms"]): row for row in report["summaries"]
    }
    add(
        "0.005 ms post hoc reference met all waveform criteria",
        bool(lookup[("fixed_step_boundary_sampling", 0.005)]["all_waveforms_meet_all_criteria"])
        and report["schema_version"] == "2.0.0"
        and "runtime_seconds" not in report
        and report["software"] == {"package_version": "0.2.1"},
        f"summary={lookup[(('fixed_step_boundary_sampling'), 0.005)]}; deterministic schema={report['schema_version']}",
    )
    add(
        "coarser 0.025 ms reference did not meet all waveform criteria",
        not lookup[("fixed_step_boundary_sampling", 0.025)]["all_waveforms_meet_all_criteria"],
        str(lookup[("fixed_step_boundary_sampling", 0.025)]),
    )

    required_phrases = (
        "one method-development specimen and five prespecified evaluation",
        "72 analysis cases",
        "122 calculated values and 94 reason-coded non-evaluable outcomes",
        "None met all transition, pulse-width, amplitude, and charge criteria",
        "all 24 original pre-stimulus periods",
        "20 of 24 cases met at least one material-change criterion",
        "0.005 and 0.0025 ms steps met the complete criteria for all five",
    )
    for phrase in required_phrases:
        add(f"manuscript includes: {phrase}", phrase in manuscript, "exact phrase search")
    if len(checks) != 25:
        raise AssertionError(f"Expected 25 scientific checks, built {len(checks)}")
    return checks, report


def _ignored_generated_path(relative: str) -> bool:
    parts = PurePosixPath(relative).parts
    return (
        any(part in {".venv", "__pycache__", ".pytest_cache", ".ruff_cache"} for part in parts)
        or any(part.endswith(".egg-info") for part in parts)
        or relative in {"benchmark.json", ".coverage"}
    )


def verify_release_manifest(root: Path, manifest_path: Path) -> int:
    root = root.resolve()
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise ValueError(f"Release manifest not found: {manifest_path}")
    rows = read_csv(manifest_path, {"relative_path", "sha256", "size_bytes"})
    seen: set[str] = set()
    for row in rows:
        relative = row["relative_path"]
        path = PurePosixPath(relative)
        if (
            not relative
            or "\\" in relative
            or path.is_absolute()
            or PureWindowsPath(relative).is_absolute()
            or bool(PureWindowsPath(relative).drive)
            or ".." in path.parts
            or relative in seen
        ):
            raise ValueError(f"Unsafe or duplicate manifest path: {relative!r}")
        seen.add(relative)
        candidate = (root / Path(*path.parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Manifest path escapes release root: {relative}") from error
        if not candidate.is_file():
            raise ValueError(f"Manifest file missing: {relative}")
        if candidate.stat().st_size != int(row["size_bytes"]):
            raise ValueError(f"Size mismatch: {relative}")
        if sha256_file(candidate) != row["sha256"].casefold():
            raise ValueError(f"SHA-256 mismatch: {relative}")

    try:
        manifest_relative = manifest_path.relative_to(root).as_posix()
    except ValueError:
        manifest_relative = ""
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.relative_to(root).as_posix() != manifest_relative
        and not _ignored_generated_path(path.relative_to(root).as_posix())
    }
    if seen != actual:
        missing = sorted(actual - seen)
        stale = sorted(seen - actual)
        raise ValueError(f"Manifest inventory mismatch: unlisted={missing}, stale={stale}")
    return len(rows)


def render_report(checks: list[Check], benchmark: dict[str, Any]) -> str:
    failed = [check for check in checks if not check.passed]
    lines = [
        "# Numerical consistency",
        "",
        f"- Scientific checks passed: **{len(checks) - len(failed)}/{len(checks)}**",
        "- Allen assets: **40 identifiers; six recording SHA-256 digests**",
        "",
        "## Constructive current-delivery benchmark",
        "",
        "| Playback method | Solver step (ms) | Waveforms meeting all criteria | All five |",
        "|---|---:|---:|---|",
    ]
    for row in benchmark["summaries"]:
        step = "event times" if row["solver_dt_ms"] is None else str(row["solver_dt_ms"])
        lines.append(
            f"| {row['current_playback_method'].replace('_', ' ')} | {step} | "
            f"{row['waveforms_meeting_all_criteria']}/{row['waveform_count']} | "
            f"{'Yes' if row['all_waveforms_meet_all_criteria'] else 'No'} |"
        )
    lines.extend(
        [
            "",
            "The benchmark is model-free. It does not execute NEURON or the 24 perisomatic cases.",
            "",
            "## Manuscript and table checks",
            "",
            "| Check | Result | Evidence |",
            "|---|---|---|",
        ]
    )
    lines.extend(
        f"| {check.name} | {'PASS' if check.passed else 'FAIL'} | "
        f"{check.evidence.replace('|', '/')} |"
        for check in checks
    )
    lines.extend(
        [
            "",
            "These checks compare included claims with committed CSV and JSON outputs. They do not",
            "rerun the Allen-data simulations or establish clean-machine reproduction.",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO)
    parser.add_argument("--manifest", type=Path, default=Path("PUBLIC_RELEASE_SHA256.csv"))
    parser.add_argument("--science-only", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        asset_count = validate_allen_assets(root)
        checks, benchmark = scientific_checks(root)
        failed = [check for check in checks if not check.passed]
        if failed:
            names = "; ".join(check.name for check in failed)
            raise ValueError(f"Scientific checks failed: {names}")
        manifest_count: int | None = None
        if not args.science_only:
            manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
            manifest_count = verify_release_manifest(root, manifest)
        if args.report:
            report_path = args.report if args.report.is_absolute() else root / args.report
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_report(checks, benchmark), encoding="utf-8")
        package_text = (
            "" if manifest_count is None else f"; {manifest_count} package files verified"
        )
        print(f"PASS: {len(checks)} scientific checks; {asset_count} Allen assets{package_text}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, csv.Error) as error:
        print(f"FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
