"""Run the data-free current-delivery benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from neuronal_model_replay_validation import run_constructive_benchmark, write_json_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_constructive_benchmark()
    passing = [row for row in report["summaries"] if row["all_waveforms_meet_all_criteria"]]
    if len(report["results"]) != 25 or len(passing) != 3:
        raise ValueError("Unexpected benchmark result dimensions")
    if args.output:
        write_json_report(report, args.output)
    print(f"PASS: {len(report['results'])} results; {len(passing)} qualifying configurations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
