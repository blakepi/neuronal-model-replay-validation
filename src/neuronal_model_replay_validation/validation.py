"""Numerical checks for neuronal current playback and model initialization.

The synthetic benchmark is independent of Allen Institute data.  It represents commands as
piecewise-constant signals, applies playback methods, and evaluates transition timing, pulse
width, boundary amplitude, and interval charge without changing the acceptance criteria after
observing results.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TIME_TOLERANCE_MS = 1e-9
AMPLITUDE_TOLERANCE_NA = 1e-12
CHARGE_ABSOLUTE_TOLERANCE_NA_MS = 1e-12
CHARGE_RELATIVE_TOLERANCE = 1e-9
GRID_ALIGNMENT_TOLERANCE_STEPS = 1e-10
REPORT_SCHEMA_VERSION = "2.0.0"
PACKAGE_VERSION = "0.2.1"


@dataclass(frozen=True)
class BenchmarkWaveform:
    """A piecewise-constant source command sampled at ``source_dt_ms``."""

    name: str
    source_dt_ms: float
    values_nA: tuple[float, ...]
    expected_pulses_ms: tuple[tuple[float, float], ...] = ()

    @property
    def duration_ms(self) -> float:
        return len(self.values_nA) * self.source_dt_ms


@dataclass(frozen=True)
class PlaybackSignal:
    """Delivered values at the times when a playback implementation can update them."""

    method: str
    update_times_ms: tuple[float, ...]
    values_nA: tuple[float, ...]
    duration_ms: float
    solver_dt_ms: float | None


def _waveform_values(
    source_dt_ms: float,
    duration_ms: float,
    intervals: Sequence[tuple[float, float, float]],
) -> tuple[float, ...]:
    count = int(round(duration_ms / source_dt_ms))
    return tuple(
        next(
            (
                amplitude
                for onset, offset, amplitude in intervals
                if onset - TIME_TOLERANCE_MS <= index * source_dt_ms < offset - TIME_TOLERANCE_MS
            ),
            0.0,
        )
        for index in range(count)
    )


BENCHMARK_WAVEFORMS = (
    BenchmarkWaveform(
        "exact_boundary",
        0.025,
        _waveform_values(0.025, 0.25, ((0.05, 0.10, 1.0), (0.15, 0.20, 0.5))),
        ((0.05, 0.10), (0.15, 0.20)),
    ),
    BenchmarkWaveform(
        "one_source_sample_offset",
        0.005,
        _waveform_values(0.005, 0.15, ((0.03, 0.055, 1.0), (0.08, 0.105, 0.5))),
        ((0.03, 0.055), (0.08, 0.105)),
    ),
    BenchmarkWaveform(
        "midpoint_between_solver_steps",
        0.0125,
        _waveform_values(0.0125, 0.15, ((0.0125, 0.0375, 1.0), (0.0625, 0.0875, 0.5))),
        ((0.0125, 0.0375), (0.0625, 0.0875)),
    ),
    BenchmarkWaveform(
        "sub_solver_step_pulse",
        0.005,
        _waveform_values(0.005, 0.10, ((0.005, 0.015, 1.0),)),
        ((0.005, 0.015),),
    ),
    BenchmarkWaveform(
        "consecutive_transitions",
        0.005,
        (0.0, 1.0, -0.5, 0.75, 0.0) + (0.0,) * 15,
    ),
)


def _close(left: float, right: float, tolerance: float = AMPLITUDE_TOLERANCE_NA) -> bool:
    return abs(left - right) <= tolerance


def _finite(value: float, label: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite.")
    return result


def _validate_waveform(waveform: BenchmarkWaveform) -> None:
    source_dt_ms = _finite(waveform.source_dt_ms, "source_dt_ms")
    if source_dt_ms <= 0.0:
        raise ValueError("source_dt_ms must be positive.")
    if not waveform.values_nA:
        raise ValueError("A benchmark waveform must contain at least one value.")
    for index, value in enumerate(waveform.values_nA):
        _finite(value, f"values_nA[{index}]")
    for index, (onset, offset) in enumerate(waveform.expected_pulses_ms):
        onset = _finite(onset, f"expected_pulses_ms[{index}].onset")
        offset = _finite(offset, f"expected_pulses_ms[{index}].offset")
        if not 0.0 <= onset < offset <= waveform.duration_ms:
            raise ValueError("Expected pulse edges must lie within the waveform duration.")


def _validate_signal(waveform: BenchmarkWaveform, signal: PlaybackSignal) -> None:
    _validate_waveform(waveform)
    duration_ms = _finite(signal.duration_ms, "duration_ms")
    if duration_ms <= 0.0:
        raise ValueError("duration_ms must be positive.")
    if not math.isclose(duration_ms, waveform.duration_ms, rel_tol=0.0, abs_tol=TIME_TOLERANCE_MS):
        raise ValueError("Signal and waveform durations must match.")
    if len(signal.update_times_ms) != len(signal.values_nA) or not signal.values_nA:
        raise ValueError("Signal times and values must be nonempty and equal in length.")
    times = [
        _finite(value, f"update_times_ms[{index}]")
        for index, value in enumerate(signal.update_times_ms)
    ]
    for index, value in enumerate(signal.values_nA):
        _finite(value, f"signal.values_nA[{index}]")
    if abs(times[0]) > TIME_TOLERANCE_MS:
        raise ValueError("The first signal update must occur at 0 ms.")
    if any(right <= left for left, right in zip(times, times[1:], strict=False)):
        raise ValueError("Signal update times must be strictly increasing.")
    if times[0] < -TIME_TOLERANCE_MS or times[-1] >= duration_ms:
        raise ValueError("Signal update times must lie in [0, duration_ms).")
    if signal.solver_dt_ms is not None:
        solver_dt_ms = _finite(signal.solver_dt_ms, "solver_dt_ms")
        if solver_dt_ms <= 0.0:
            raise ValueError("solver_dt_ms must be positive.")


def _sample_times(duration_ms: float, step_ms: float) -> tuple[float, ...]:
    duration_ms = _finite(duration_ms, "duration_ms")
    step_ms = _finite(step_ms, "step_ms")
    if duration_ms <= 0:
        raise ValueError("The duration must be positive.")
    if step_ms <= 0:
        raise ValueError("The solver step must be positive.")
    count = int(math.ceil(duration_ms / step_ms - TIME_TOLERANCE_MS))
    return tuple(index * step_ms for index in range(count))


def source_value(waveform: BenchmarkWaveform, time_ms: float) -> float:
    """Return the zero-order-held source value at one time."""

    _validate_waveform(waveform)
    time_ms = _finite(time_ms, "time_ms")
    if not 0.0 <= time_ms < waveform.duration_ms:
        raise ValueError("time_ms must lie in [0, waveform.duration_ms).")
    index = min(
        int(math.floor((time_ms + TIME_TOLERANCE_MS) / waveform.source_dt_ms)),
        len(waveform.values_nA) - 1,
    )
    return waveform.values_nA[index]


def fixed_step_boundary_sampling(
    waveform: BenchmarkWaveform, solver_dt_ms: float
) -> PlaybackSignal:
    """Sample the piecewise-constant command at each fixed solver boundary."""

    _validate_waveform(waveform)
    times = _sample_times(waveform.duration_ms, solver_dt_ms)
    return PlaybackSignal(
        method="fixed_step_boundary_sampling",
        update_times_ms=times,
        values_nA=tuple(source_value(waveform, value) for value in times),
        duration_ms=waveform.duration_ms,
        solver_dt_ms=solver_dt_ms,
    )


def event_scheduled_transitions(waveform: BenchmarkWaveform) -> PlaybackSignal:
    """Apply each source transition at its source time with no interpolation."""

    _validate_waveform(waveform)
    times = tuple(index * waveform.source_dt_ms for index in range(len(waveform.values_nA)))
    return PlaybackSignal(
        method="event_scheduled_transitions",
        update_times_ms=times,
        values_nA=waveform.values_nA,
        duration_ms=waveform.duration_ms,
        solver_dt_ms=None,
    )


def _transitions(times: Sequence[float], values: Sequence[float]) -> list[tuple[float, float]]:
    if len(times) != len(values) or not values:
        raise ValueError("Signal times and values must be nonempty and equal in length.")
    checked_times = [_finite(value, f"times[{index}]") for index, value in enumerate(times)]
    checked_values = [_finite(value, f"values[{index}]") for index, value in enumerate(values)]
    if any(right <= left for left, right in zip(checked_times, checked_times[1:], strict=False)):
        raise ValueError("Signal times must be strictly increasing.")
    output: list[tuple[float, float]] = []
    previous = checked_values[0]
    for update_time, current in zip(checked_times[1:], checked_values[1:], strict=True):
        if not _close(current, previous):
            output.append((update_time, current))
            previous = current
    return output


def _active_periods(signal: PlaybackSignal) -> list[tuple[float, float]]:
    periods: list[tuple[float, float]] = []
    active_start: float | None = None
    for update_time, value in zip(signal.update_times_ms, signal.values_nA, strict=True):
        active = not _close(value, 0.0)
        if active and active_start is None:
            active_start = update_time
        elif not active and active_start is not None:
            periods.append((active_start, update_time))
            active_start = None
    if active_start is not None:
        periods.append((active_start, signal.duration_ms))
    return periods


def _integrated_charge(signal: PlaybackSignal) -> float:
    stops = (*signal.update_times_ms[1:], signal.duration_ms)
    return sum(
        value * max(0.0, stop - start)
        for start, stop, value in zip(signal.update_times_ms, stops, signal.values_nA, strict=True)
    )


def evaluate_playback(waveform: BenchmarkWaveform, signal: PlaybackSignal) -> dict[str, Any]:
    """Apply the complete waveform-reproduction criteria to one delivered signal."""

    _validate_signal(waveform, signal)
    expected_transitions = _transitions(
        tuple(index * waveform.source_dt_ms for index in range(len(waveform.values_nA))),
        waveform.values_nA,
    )
    observed_transitions = _transitions(signal.update_times_ms, signal.values_nA)
    transition_details: list[dict[str, Any]] = []
    transition_criterion_met = len(expected_transitions) == len(observed_transitions)
    for index in range(max(len(expected_transitions), len(observed_transitions))):
        if index >= len(expected_transitions) or index >= len(observed_transitions):
            transition_details.append({"index": index, "comparison": "missing_or_extra_transition"})
            continue
        expected_time, expected_value = expected_transitions[index]
        observed_time, observed_value = observed_transitions[index]
        timing_error = observed_time - expected_time
        if signal.solver_dt_ms is None:
            timing_met = abs(timing_error) <= TIME_TOLERANCE_MS
        else:
            aligned = (
                abs(
                    expected_time / signal.solver_dt_ms - round(expected_time / signal.solver_dt_ms)
                )
                <= GRID_ALIGNMENT_TOLERANCE_STEPS
            )
            timing_met = (
                abs(timing_error) <= TIME_TOLERANCE_MS
                if aligned
                else -TIME_TOLERANCE_MS <= timing_error < signal.solver_dt_ms - TIME_TOLERANCE_MS
            )
        amplitude_met = _close(expected_value, observed_value)
        transition_criterion_met &= timing_met and amplitude_met
        transition_details.append(
            {
                "index": index,
                "source_time_ms": expected_time,
                "delivered_time_ms": observed_time,
                "timing_error_ms": timing_error,
                "source_value_nA": expected_value,
                "delivered_value_nA": observed_value,
                "timing_criterion_met": timing_met,
                "amplitude_criterion_met": amplitude_met,
            }
        )

    observed_pulses = _active_periods(signal)
    pulse_details: list[dict[str, Any]] = []
    pulse_criterion_met = (
        True
        if not waveform.expected_pulses_ms
        else len(waveform.expected_pulses_ms) == len(observed_pulses)
    )
    comparison_count = (
        0
        if not waveform.expected_pulses_ms
        else max(len(waveform.expected_pulses_ms), len(observed_pulses))
    )
    for index in range(comparison_count):
        if index >= len(waveform.expected_pulses_ms) or index >= len(observed_pulses):
            pulse_details.append({"index": index, "comparison": "missing_or_extra_pulse"})
            continue
        source_on, source_off = waveform.expected_pulses_ms[index]
        delivered_on, delivered_off = observed_pulses[index]
        width_error = (delivered_off - delivered_on) - (source_off - source_on)
        if signal.solver_dt_ms is None:
            tolerance = TIME_TOLERANCE_MS
        else:
            aligned = all(
                abs(edge / signal.solver_dt_ms - round(edge / signal.solver_dt_ms))
                <= GRID_ALIGNMENT_TOLERANCE_STEPS
                for edge in (source_on, source_off)
            )
            tolerance = TIME_TOLERANCE_MS if aligned else signal.solver_dt_ms - TIME_TOLERANCE_MS
        width_met = abs(width_error) <= tolerance
        pulse_criterion_met &= width_met
        pulse_details.append(
            {
                "index": index,
                "source_width_ms": source_off - source_on,
                "delivered_width_ms": delivered_off - delivered_on,
                "width_error_ms": width_error,
                "width_criterion_met": width_met,
            }
        )

    source_charge = sum(waveform.values_nA) * waveform.source_dt_ms
    delivered_charge = _integrated_charge(signal)
    charge_error = delivered_charge - source_charge
    charge_tolerance = max(
        CHARGE_ABSOLUTE_TOLERANCE_NA_MS,
        CHARGE_RELATIVE_TOLERANCE * abs(source_charge),
    )
    charge_criterion_met = abs(charge_error) <= charge_tolerance
    amplitude_criterion_met = all(
        detail.get("amplitude_criterion_met", True) for detail in transition_details
    )
    all_criteria_met = bool(
        transition_criterion_met
        and pulse_criterion_met
        and amplitude_criterion_met
        and charge_criterion_met
    )
    return {
        "benchmark_waveform": waveform.name,
        "current_playback_method": signal.method,
        "solver_dt_ms": signal.solver_dt_ms,
        "transition_criterion_met": transition_criterion_met,
        "pulse_width_criterion_met": pulse_criterion_met,
        "boundary_amplitude_criterion_met": amplitude_criterion_met,
        "interval_charge_criterion_met": charge_criterion_met,
        "all_criteria_met": all_criteria_met,
        "source_charge_nA_ms": source_charge,
        "delivered_charge_nA_ms": delivered_charge,
        "charge_error_nA_ms": charge_error,
        "transition_details": transition_details,
        "pulse_details": pulse_details,
    }


def run_constructive_benchmark(
    solver_steps_ms: Iterable[float] = (0.025, 0.0125, 0.005, 0.0025),
) -> dict[str, Any]:
    """Run post hoc fixed-step and event-scheduled extensions on all five waveforms."""

    solver_steps = tuple(
        sorted((_finite(value, "solver_steps_ms") for value in solver_steps_ms), reverse=True)
    )
    if not solver_steps:
        raise ValueError("At least one solver step is required.")
    if any(value <= 0.0 for value in solver_steps):
        raise ValueError("Solver steps must be positive.")
    if len(set(solver_steps)) != len(solver_steps):
        raise ValueError("Solver steps must be unique.")
    results: list[dict[str, Any]] = []
    for solver_dt_ms in solver_steps:
        for waveform in BENCHMARK_WAVEFORMS:
            results.append(
                evaluate_playback(waveform, fixed_step_boundary_sampling(waveform, solver_dt_ms))
            )
    for waveform in BENCHMARK_WAVEFORMS:
        results.append(evaluate_playback(waveform, event_scheduled_transitions(waveform)))
    summaries: list[dict[str, Any]] = []
    keys = sorted({(row["current_playback_method"], row["solver_dt_ms"]) for row in results})
    for method, solver_dt_ms in keys:
        selected = [
            row
            for row in results
            if row["current_playback_method"] == method and row["solver_dt_ms"] == solver_dt_ms
        ]
        summaries.append(
            {
                "current_playback_method": method,
                "solver_dt_ms": solver_dt_ms,
                "waveforms_meeting_all_criteria": sum(row["all_criteria_met"] for row in selected),
                "waveform_count": len(selected),
                "all_waveforms_meet_all_criteria": all(row["all_criteria_met"] for row in selected),
            }
        )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "analysis_label": "post_hoc_methodological_extension",
        "criteria": {
            "time_tolerance_ms": TIME_TOLERANCE_MS,
            "amplitude_tolerance_nA": AMPLITUDE_TOLERANCE_NA,
            "charge_absolute_tolerance_nA_ms": CHARGE_ABSOLUTE_TOLERANCE_NA_MS,
            "charge_relative_tolerance": CHARGE_RELATIVE_TOLERANCE,
        },
        "software": {"package_version": PACKAGE_VERSION},
        "summaries": summaries,
        "results": results,
    }


def assess_equilibration_window(
    time_ms: Sequence[float],
    values: Sequence[float],
    *,
    window_ms: float,
    maximum_abs_slope_per_ms: float,
    maximum_span: float,
) -> dict[str, Any]:
    """Require the final two non-overlapping windows to satisfy slope and span limits."""

    if len(time_ms) != len(values) or len(time_ms) < 2:
        raise ValueError(
            "Time and trajectory arrays must have equal length and at least two values."
        )
    checked_time = [_finite(value, f"time_ms[{index}]") for index, value in enumerate(time_ms)]
    checked_values = [_finite(value, f"values[{index}]") for index, value in enumerate(values)]
    window_ms = _finite(window_ms, "window_ms")
    maximum_abs_slope_per_ms = _finite(
        maximum_abs_slope_per_ms, "maximum_abs_slope_per_ms"
    )
    maximum_span = _finite(maximum_span, "maximum_span")
    if window_ms <= 0.0:
        raise ValueError("window_ms must be positive.")
    if maximum_abs_slope_per_ms < 0.0 or maximum_span < 0.0:
        raise ValueError("Equilibration thresholds must be nonnegative.")
    if any(right <= left for left, right in zip(checked_time, checked_time[1:], strict=False)):
        raise ValueError("Time values must be strictly increasing.")
    final_end = checked_time[-1]
    first_start = final_end - 2.0 * window_ms
    if checked_time[0] > first_start + TIME_TOLERANCE_MS:
        raise ValueError("Two complete consecutive windows are unavailable.")

    windows: list[dict[str, Any]] = []
    for index in range(2):
        lower = first_start + index * window_ms
        upper = lower + window_ms
        selected = [
            (time_value, value)
            for time_value, value in zip(checked_time, checked_values, strict=True)
            if lower - TIME_TOLERANCE_MS <= time_value <= upper + TIME_TOLERANCE_MS
        ]
        if len(selected) < 2 or selected[-1][0] - selected[0][0] < window_ms - TIME_TOLERANCE_MS:
            raise ValueError("Two complete consecutive windows are unavailable.")
        selected_time = [row[0] for row in selected]
        selected_values = [row[1] for row in selected]
        mean_time = sum(selected_time) / len(selected_time)
        mean_value = sum(selected_values) / len(selected_values)
        denominator = sum((value - mean_time) ** 2 for value in selected_time)
        if denominator <= 0.0:
            raise ValueError("Window time variance must be positive.")
        slope = (
            sum(
                (time_value - mean_time) * (value - mean_value)
                for time_value, value in selected
            )
            / denominator
        )
        span = max(selected_values) - min(selected_values)
        windows.append(
            {
                "window_index": index + 1,
                "start_ms": lower,
                "end_ms": upper,
                "sample_count": len(selected),
                "ols_slope_per_ms": slope,
                "span": span,
                "passed": (
                    abs(slope) <= maximum_abs_slope_per_ms and span <= maximum_span
                ),
            }
        )
    final_window = windows[-1]
    consecutive_passing_windows = 0
    for window in reversed(windows):
        if not window["passed"]:
            break
        consecutive_passing_windows += 1
    return {
        "sample_count": final_window["sample_count"],
        "window_ms": window_ms,
        "ols_slope_per_ms": final_window["ols_slope_per_ms"],
        "span": final_window["span"],
        "maximum_abs_slope_per_ms": maximum_abs_slope_per_ms,
        "maximum_span": maximum_span,
        "required_consecutive_windows": 2,
        "consecutive_passing_windows": consecutive_passing_windows,
        "windows": windows,
        "equilibrated": consecutive_passing_windows == 2,
    }


def outcome_eligibility(
    outcome: str,
    *,
    recording_spike_count: int | None = None,
    model_spike_count: int | None = None,
    protocol: str | None = None,
    minimum_coverage: float = 0.80,
    coverage_values: Sequence[float] = (),
) -> dict[str, str]:
    """Return a public, reason-coded eligibility state for a prespecified outcome."""

    def validate_spike_count(value: int | None, label: str) -> None:
        if value is None:
            return
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{label} must be an integer or None.")
        if value < 0:
            raise ValueError(f"{label} must be nonnegative.")

    validate_spike_count(recording_spike_count, "recording_spike_count")
    validate_spike_count(model_spike_count, "model_spike_count")
    minimum_coverage = _finite(minimum_coverage, "minimum_coverage")
    if not 0.0 <= minimum_coverage <= 1.0:
        raise ValueError("minimum_coverage must lie in [0, 1].")
    checked_coverage = tuple(
        _finite(value, f"coverage_values[{index}]")
        for index, value in enumerate(coverage_values)
    )

    def state(
        status: str,
        reason: str,
        category: str,
        rule: str,
    ) -> dict[str, str]:
        return {
            "status": status,
            "non_evaluable_reason": reason,
            "non_evaluable_category": category,
            "applicability_rule": rule,
        }

    if outcome == "absolute_spike_count_error":
        return state("calculated", "", "calculated", "unconditional")
    if outcome == "absolute_first_spike_latency_error_ms":
        if recording_spike_count is None or model_spike_count is None:
            raise ValueError("Both spike counts are required for first-spike latency eligibility.")
        if recording_spike_count == 0 or model_spike_count == 0:
            return state(
                "non_evaluable",
                "no_in_window_spike",
                "conditional_spike_absence",
                "conditional_on_recording_and_model_spikes",
            )
        return state(
            "calculated",
            "",
            "calculated",
            "conditional_on_recording_and_model_spikes",
        )
    if outcome == "absolute_steady_state_delta_voltage_error_mV":
        normalized_protocol = (protocol or "").strip().casefold().replace(" ", "_")
        steady_state_protocols = {"long_square", "square_-_2s_suprathreshold"}
        if normalized_protocol not in steady_state_protocols:
            return state(
                "non_evaluable",
                "not_applicable_to_protocol",
                "protocol_structural",
                "long_square_coverage_contract",
            )
        if len(checked_coverage) != 4:
            raise ValueError("Four coverage values are required for Long Square eligibility.")
        if any(value < minimum_coverage for value in checked_coverage):
            return state(
                "non_evaluable",
                "insufficient_coverage",
                "scientific_output_induced",
                "long_square_coverage_contract",
            )
        return state(
            "calculated", "", "calculated", "long_square_coverage_contract"
        )
    raise ValueError(f"Unknown outcome: {outcome}")


def write_json_report(report: Mapping[str, Any], output: Path) -> None:
    """Write a stable, human-readable JSON report."""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run neuronal numerical-validation checks."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    benchmark = subparsers.add_parser(
        "benchmark", description="Run synthetic current-delivery benchmarks without external data."
    )
    benchmark.add_argument("--output", type=Path, required=True, help="JSON report path.")
    args = parser.parse_args(argv)
    if args.command == "benchmark":
        report = run_constructive_benchmark()
        write_json_report(report, args.output)
        passing = [row for row in report["summaries"] if row["all_waveforms_meet_all_criteria"]]
        print(
            f"Wrote {args.output}; {len(passing)} tested configurations met all waveform criteria."
        )
        return 0
    return 2


def main() -> None:
    """Console-script entry point."""

    raise SystemExit(_main())


if __name__ == "__main__":
    main()
