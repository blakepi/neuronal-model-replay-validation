# Numerical consistency

- Scientific checks passed: **25/25**
- Allen assets: **40 identifiers; six recording SHA-256 digests**

## Constructive current-delivery benchmark

| Playback method | Solver step (ms) | Waveforms meeting all criteria | All five |
|---|---:|---:|---|
| event scheduled transitions | event times | 5/5 | Yes |
| fixed step boundary sampling | 0.0025 | 5/5 | Yes |
| fixed step boundary sampling | 0.005 | 5/5 | Yes |
| fixed step boundary sampling | 0.0125 | 3/5 | No |
| fixed step boundary sampling | 0.025 | 3/5 | No |

The benchmark is model-free. It does not execute NEURON or the 24 perisomatic cases.

## Manuscript and table checks

| Check | Result | Evidence |
|---|---|---|
| six cells | PASS | table rows=6 |
| one method-development and five evaluation specimens | PASS | strata={'method_development': 1, 'evaluation': 5} |
| 24 recording selections | PASS | unique selections=24; cross-table consistent=True |
| three simulation conditions | PASS | conditions=['glif_recording_grid', 'glif_stored_grid', 'perisomatic_recording_grid_playback'] |
| 72 analysis cases | PASS | case rows=72; unique=True; normalized dt=True |
| 216 outcome records | PASS | rows=216; unique and controlled=True |
| 122 calculated outcomes | PASS | {'calculated': 122, 'non_evaluable': 94} |
| 94 non-evaluable outcomes | PASS | statuses={'calculated': 122, 'non_evaluable': 94}; exact public contract=True |
| five original playback methods | PASS | rows=5 |
| five benchmark waveforms | PASS | ['consecutive_transitions', 'exact_boundary', 'midpoint_between_solver_steps', 'one_source_sample_offset', 'sub_solver_step_pulse'] |
| no original method met all five criteria | PASS | all-five values=['False', 'False', 'False', 'False', 'False'] |
| 24 initialization cases | PASS | rows=24 |
| all 24 original periods drifted | PASS | drifting=24 |
| all 24 extended periods converged | PASS | converged=24 |
| 20 cases met a material-change criterion | PASS | criterion met=20 |
| all six cells had at least three affected selections | PASS | [3, 3, 3, 4, 4, 3] |
| 0.005 ms post hoc reference met all waveform criteria | PASS | summary={'all_waveforms_meet_all_criteria': True, 'current_playback_method': 'fixed_step_boundary_sampling', 'solver_dt_ms': 0.005, 'waveform_count': 5, 'waveforms_meeting_all_criteria': 5}; deterministic schema=2.0.0 |
| coarser 0.025 ms reference did not meet all waveform criteria | PASS | {'all_waveforms_meet_all_criteria': False, 'current_playback_method': 'fixed_step_boundary_sampling', 'solver_dt_ms': 0.025, 'waveform_count': 5, 'waveforms_meeting_all_criteria': 3} |
| manuscript includes: one method-development specimen and five prespecified evaluation | PASS | exact phrase search |
| manuscript includes: 72 analysis cases | PASS | exact phrase search |
| manuscript includes: 122 calculated values and 94 reason-coded non-evaluable outcomes | PASS | exact phrase search |
| manuscript includes: None met all transition, pulse-width, amplitude, and charge criteria | PASS | exact phrase search |
| manuscript includes: all 24 original pre-stimulus periods | PASS | exact phrase search |
| manuscript includes: 20 of 24 cases met at least one material-change criterion | PASS | exact phrase search |
| manuscript includes: 0.005 and 0.0025 ms steps met the complete criteria for all five | PASS | exact phrase search |

These checks compare included claims with committed CSV and JSON outputs. They do not
rerun the Allen-data simulations or establish clean-machine reproduction.
