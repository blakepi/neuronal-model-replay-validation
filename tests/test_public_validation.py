from __future__ import annotations

import json
import math

import pytest

from neuronal_model_replay_validation import (
    BENCHMARK_WAVEFORMS,
    BenchmarkWaveform,
    PlaybackSignal,
    assess_equilibration_window,
    evaluate_playback,
    outcome_eligibility,
    run_constructive_benchmark,
    source_value,
    write_json_report,
)


def test_constructive_benchmark_preserves_five_waveforms() -> None:
    report = run_constructive_benchmark()
    assert len(BENCHMARK_WAVEFORMS) == 5
    assert len(report["results"]) == 25
    assert {row["benchmark_waveform"] for row in report["results"]} == {
        waveform.name for waveform in BENCHMARK_WAVEFORMS
    }


def test_source_resolution_and_finer_steps_meet_unchanged_criteria() -> None:
    report = run_constructive_benchmark()
    summaries = {
        (row["current_playback_method"], row["solver_dt_ms"]): row for row in report["summaries"]
    }
    assert (
        summaries[("fixed_step_boundary_sampling", 0.025)]["all_waveforms_meet_all_criteria"]
        is False
    )
    assert (
        summaries[("fixed_step_boundary_sampling", 0.005)]["all_waveforms_meet_all_criteria"]
        is True
    )
    assert (
        summaries[("fixed_step_boundary_sampling", 0.0025)]["all_waveforms_meet_all_criteria"]
        is True
    )
    assert (
        summaries[("event_scheduled_transitions", None)]["all_waveforms_meet_all_criteria"] is True
    )


def test_equilibration_window_reports_slope_span_and_state() -> None:
    result = assess_equilibration_window(
        [0.0, 1.0, 2.0, 3.0, 4.0],
        [-65.0, -65.0, -65.0, -65.0, -65.0],
        window_ms=2.0,
        maximum_abs_slope_per_ms=0.01,
        maximum_span=0.2,
    )
    assert result["ols_slope_per_ms"] == pytest.approx(0.0)
    assert result["span"] == pytest.approx(0.0)
    assert result["required_consecutive_windows"] == 2
    assert result["consecutive_passing_windows"] == 2
    assert result["equilibrated"] is True


def test_equilibration_rejects_single_passing_window_shortcut() -> None:
    result = assess_equilibration_window(
        [0.0, 1.0, 2.0, 3.0, 4.0],
        [-66.0, -65.5, -65.0, -65.0, -65.0],
        window_ms=2.0,
        maximum_abs_slope_per_ms=0.01,
        maximum_span=0.2,
    )
    assert [window["passed"] for window in result["windows"]] == [False, True]
    assert result["consecutive_passing_windows"] == 1
    assert result["equilibrated"] is False


def test_outcome_eligibility_is_reason_coded() -> None:
    assert outcome_eligibility(
        "absolute_first_spike_latency_error_ms",
        recording_spike_count=1,
        model_spike_count=0,
    ) == {
        "status": "non_evaluable",
        "non_evaluable_reason": "no_in_window_spike",
        "non_evaluable_category": "conditional_spike_absence",
        "applicability_rule": "conditional_on_recording_and_model_spikes",
    }
    assert (
        outcome_eligibility(
            "absolute_steady_state_delta_voltage_error_mV",
            protocol="Long Square",
            coverage_values=(1.0, 1.0, 0.9, 0.95),
        )["status"]
        == "calculated"
    )


@pytest.mark.parametrize("bad_count", [-1, -100])
def test_outcome_eligibility_rejects_negative_spike_counts(bad_count: int) -> None:
    with pytest.raises(ValueError, match="must be nonnegative"):
        outcome_eligibility(
            "absolute_first_spike_latency_error_ms",
            recording_spike_count=bad_count,
            model_spike_count=1,
        )


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_public_numerical_interfaces_reject_nonfinite_values(bad_value: float) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        source_value(BENCHMARK_WAVEFORMS[0], bad_value)
    with pytest.raises(ValueError, match="must be finite"):
        assess_equilibration_window(
            [0.0, 1.0, 2.0, 3.0, 4.0],
            [-65.0, -65.0, bad_value, -65.0, -65.0],
            window_ms=2.0,
            maximum_abs_slope_per_ms=0.01,
            maximum_span=0.2,
        )
    with pytest.raises(ValueError, match="must be finite"):
        outcome_eligibility(
            "absolute_steady_state_delta_voltage_error_mV",
            protocol="Long Square",
            coverage_values=(1.0, 1.0, 1.0, bad_value),
        )


def test_nonpositive_time_steps_are_rejected() -> None:
    with pytest.raises(ValueError, match="must be positive"):
        run_constructive_benchmark((0.0,))
    bad_waveform = BenchmarkWaveform("bad", 0.0, (0.0,))
    bad_signal = PlaybackSignal("bad", (0.0,), (0.0,), 1.0, 0.1)
    with pytest.raises(ValueError, match="source_dt_ms must be positive"):
        evaluate_playback(bad_waveform, bad_signal)


def test_pulse_width_uses_the_documented_aligned_tolerance() -> None:
    waveform = BenchmarkWaveform(
        "aligned_tolerance_probe",
        0.1,
        (0.0, 1.0, 0.0),
        ((0.1, 0.2),),
    )
    signal = PlaybackSignal(
        "event_probe",
        (0.0, 0.1, 0.2000000015),
        (0.0, 1.0, 0.0),
        0.3,
        None,
    )
    result = evaluate_playback(waveform, signal)
    assert result["pulse_details"][0]["width_error_ms"] > 1e-9
    assert result["pulse_width_criterion_met"] is False


def test_json_report_round_trip(tmp_path) -> None:
    output = tmp_path / "benchmark.json"
    report = run_constructive_benchmark((0.005,))
    write_json_report(report, output)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == "2.0.0"
    assert len(loaded["results"]) == 10


def test_json_report_is_strict_and_byte_stable(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_json_report(run_constructive_benchmark((0.005,)), first)
    write_json_report(run_constructive_benchmark((0.005,)), second)
    assert first.read_bytes() == second.read_bytes()
    with pytest.raises(ValueError, match="Out of range float values"):
        write_json_report({"not_json": math.nan}, tmp_path / "nan.json")
