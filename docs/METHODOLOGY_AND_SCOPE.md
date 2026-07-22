# Methodology and scope

## Source command and playback references

For source interval `Δt_s`, sample `i` applies on the half-open interval
`[i Δt_s, (i + 1) Δt_s)`. A transition occurs at the first source time whose value differs from the
preceding value by more than `1e-12 nA`. The five synthetic waveforms test exact solver boundaries,
one-source-sample offsets, midpoint transitions, pulses shorter than the original solver step, and
multiple consecutive transitions.

Fixed-step boundary sampling evaluates the zero-order-held source command at each solver boundary.
The post hoc study tests solver steps of 0.025, 0.0125, 0.005, and 0.0025 ms. The event-timed
reference applies every transition at its source time without interpolation or smoothing. It is a
mathematical piecewise-constant reference, not a claimed simulator mechanism.

## Acceptance criteria

A method-waveform result meets the complete criteria only when all applicable checks pass:

1. Delivered transition count equals source transition count.
2. Transition amplitudes agree within `1e-12 nA`.
3. A solver-grid transition has timing error no greater than `1e-9 ms`; a nonaligned transition may
   move forward by less than one solver step.
4. Prespecified nonzero pulse count and width are preserved. Aligned pulse edges use the strict time
   tolerance; nonaligned edges use a tolerance smaller than one solver step.
5. Integrated charge agrees within the larger of `1e-12 nA ms` and `1e-9` times the absolute source
   charge.

A playback configuration meets the benchmark only when all five waveforms meet the complete
criteria. The criteria are unchanged between the original negative benchmark and the constructive
extensions.

## Equilibration and material change

For a final window of duration `W`, ordinary least-squares slope and span are calculated for each
required voltage, state, clamp-current, or membrane-current trajectory. A trajectory is stable only
when every value is finite and both absolute slope and span are within the configured limits. The
six-cell analysis used final 100 ms windows and required two consecutive passing windows.

Material change is evaluated separately from convergence. A case meets the criterion when its
stimulus-window spike count changes, a comparable event shifts by at least 0.025 ms, outcome coverage
changes, or comparable steady-state voltage shifts by at least 0.5 mV.

## Outcome eligibility

- Spike-count error is calculated for every prespecified case.
- First-spike latency error uses `no_in_window_spike` when either trace lacks an in-window spike.
- Steady-state voltage error uses `not_applicable_to_protocol` outside eligible long-duration
  protocols (`Long Square` and the method-development `Square - 2s Suprathreshold` label) and
  `insufficient_coverage` when any required window has less than 0.80 usable coverage.

The public schema uses only `calculated` and `non_evaluable` status values. Non-evaluable outcomes
retain one of the three controlled reasons above and are never converted to zero or a penalty.

## Interpretation

Repeatability, stimulus-delivery fidelity, state equilibration, and physiological interpretation are
separate questions. A positive result at one level does not imply a positive result at the next. The
constructive benchmark identifies numerical reference signals; it does not establish a working
NEURON adapter or biological correctness. Equilibration sensitivity demonstrates dependence on
pre-stimulus duration, not the biologically correct initial state.

Cells are the analysis units. Sweeps and simulation conditions are nested technical observations,
not independent biological replicates. The six-cell findings are case-specific.

## Limitations

- Six operationally selected cells do not represent mouse cortex or support population inference.
- The method-development specimen is excluded from the five-specimen evaluation set.
- Exposure of individual recording sweeps during model fitting is unknown.
- The GLIF comparison changes both input sampling and model time step.
- Findings are specific to the tested implementations, versions, and criteria.
- The constructive playback references have not been implemented as verified NEURON injection
  routes or applied to the 24 perisomatic cases.
- The analysis does not identify a biologically correct initialized state.
- Complete fresh-environment reproduction of the Allen-data workflow has not been demonstrated.
