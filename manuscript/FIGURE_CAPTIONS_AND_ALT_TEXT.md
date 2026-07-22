# Figure captions, alt text, and long descriptions

## Figure 1 — Study architecture

**Caption.** Source records, prespecified cases, outcomes, numerical evaluations, and interpretive
limits are shown in sequence. The method-development cell remains separate, and neither cases nor
sweeps are treated as biological replicates.

**Alt text.** Flow diagram from six source cells to 72 cases, 216 metric states, five numerical
evaluations, and case-specific interpretive limits. A final note states that the delivered-current
criteria were not satisfied and that the equilibration analysis compares two initialization durations.

**Long description.** Five boxes proceed left to right. The first states six cells from six mice,
one method-development cell, five evaluation cells, and 24 recording selections. The second divides 72 cases equally among
two GLIF conditions and one perisomatic simulation condition. The third states three outcomes per case and 216
applicability entries. The fourth lists the numerical and provenance analyses. The fifth limits interpretation to an
case-specific report with no ranking, population inference, or digital-twin validation.

## Figure 2 — Outcome eligibility summary

**Caption.** Stacked bars distinguish calculated values from non-evaluable outcomes caused by
spike absence, protocol inapplicability, or insufficient coverage across 72 cases.

**Alt text.** Three stacked bars show 72 calculated spike-count errors; 20 calculated and 52
spike-absence latency outcomes; and 30 calculated, 36 protocol-inapplicable, and six
coverage-limited steady-state outcomes.

**Long description.** Each bar contains 72 cases. All spike-count outcomes are calculated. Twenty
latency outcomes are calculated and 52 are non-evaluable because one or both traces lacked a
retained in-window spike. Thirty steady-state outcomes are calculated, 36 are not applicable to
short protocols, and six have insufficient coverage.

## Figure 3 — Case-specific GLIF spike counts

**Caption.** Recording, stored-grid GLIF, and recording-grid GLIF counts are shown for each of 20
evaluation roles. Horizontal placement uses log1p spacing; exact values are in the source table.

**Alt text.** Dot plot of raw spike counts for 20 primary roles. Most model counts are zero or one;
specimen 471087830 has two Long Square model outputs between 57 and 79 spikes.

**Long description.** Rows are grouped by evaluation specimen in prespecified order. Open circles identify
recordings, blue squares stored-grid GLIF, and orange triangles recording-grid GLIF. All five
strict Short Square rows are zero in all conditions. The high-count specimen 471087830 Long Square
rows are visually separated at the right side of the log1p-spaced axis.

## Figure 4 — Short Square boundary

**Caption.** Strict primary and post hoc sensitivity counts are shown in prespecified specimen order.
The result is specific to five traces and the prespecified detector.

**Alt text.** Five-row table-like figure: every strict primary count is zero, every post hoc
plus-0.25-millisecond count is one, thresholds occur 0.040 to 0.200 milliseconds after offset, and
upstroke is engaged at offset in every trace.

**Long description.** The figure places the strict count first and labels it primary. The post hoc
column is explicitly labeled post hoc. Each row reports the specimen/sweep, the two
counts, threshold latency after the prespecified offset, and a yes/no upstroke indicator.

## Figure 5 — Delivered-current validation benchmark

**Caption.** A 5 × 5 matrix reports whether each playback method met the complete acceptance criteria
for each synthetic benchmark waveform. No original candidate meets all five.

**Alt text.** Pass/fail matrix showing that all five methods fail sub-step pulses and consecutive
transitions; the original method also fails the exact-boundary benchmark.

**Long description.** Rows are original two-argument Vector.play, explicit discrete playback,
explicit continuous playback, manual boundary sampling, and solver-interval charge averaging.
Columns are exact boundary, one-source offset, midpoint, sub-step pulse, and consecutive
transitions. Pass and fail appear as text and contrasting fills. The best partial candidates pass
three benchmark waveforms but fail the last two.

## Figure 6 — Initialization/equilibration sensitivity

**Caption.** Each block is one of four roles per cell. M denotes a case meeting a prespecified
material-change rule; N denotes a case that did not. Every original pre-stimulus period showed drift and every
3.0 s sensitivity converged.

**Alt text.** Six-row block chart: four cells meet a material-change criterion in three of four
cases and two cells meet a criterion in four of four; every cell has at least three affected cases.

**Long description.** Rows follow prespecified cohort order. Specimens 314822529, 324493977, 471087830,
and 464188580 have three orange M blocks and one outlined N block. Specimens 473943881 and
475585413 have four orange M blocks. Each row states that all four original pre-stimulus periods
showed drift and all four extended-equilibration runs converged.

## Supplementary Figure S1 — Complete outcome-eligibility matrix

**Caption.** Each row is one of 72 cases and each column is one outcome. Codes distinguish
calculated values and outcomes that were non-evaluable because of spike absence, protocol
inapplicability, or insufficient coverage. The first 12 rows correspond to the method-development
specimen.

**Alt text.** A 72-row by three-column matrix shows spike-count error calculated everywhere,
latency often non-evaluable because one or both traces had no spike, and steady-state values
limited to Long Square cases with sufficient coverage.

**Long description.** All 72 spike-count cells are calculated. Twenty latency cells are calculated
and 52 are non-evaluable because of spike absence. Thirty steady-state cells are calculated, 36
are not applicable to short protocols, and six have insufficient coverage for specimen 471087830's
two Long Square selections across three conditions. A divider separates 12
method-development cases from 60 evaluation cases.
