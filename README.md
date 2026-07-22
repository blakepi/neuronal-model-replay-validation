# Numerical validation for cell-matched neuronal model replay

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21483417.svg)](https://doi.org/10.5281/zenodo.21483417)

This repository tests stimulus delivery, initialized-state stability, and outcome eligibility in
cell-matched neuronal model replay.

## Findings

- The case study contains six cells from six mice: one method-development specimen and five
  evaluation specimens, with 24 recording selections and 72 condition-specific cases.
- Of 216 prespecified outcome records, 122 were calculated and 94 were non-evaluable for explicit
  scientific reasons.
- None of five original playback methods met every acceptance criterion for all five synthetic
  waveforms at the original 0.025 ms solver step.
- All 24 original pre-stimulus periods showed drift under at least one criterion; every extended
  equilibration converged at 3.0 s, and 20 of 24 cases met a material-change criterion.

The six cells are an operational methods sample. The results do not support population inference,
model ranking, held-out prediction, biological correctness, or broad digital-twin validation.

## Quick start

Python 3.11 or newer is required. The benchmark uses no Allen payloads, AllenSDK, or NEURON.

```text
python -m pip install -e ".[dev]"
python -m pytest
neuronal-model-replay-validation benchmark --output benchmark.json
```

The benchmark produces 25 method-waveform results; three tested configurations meet all waveform
criteria. See [Reproducibility](docs/REPRODUCIBILITY_GUIDE.md) for package verification and data
retrieval, and [Methodology and scope](docs/METHODOLOGY_AND_SCOPE.md) for definitions and limits.

## Contents

- `src/neuronal_model_replay_validation/`: benchmark library and command-line interface.
- `scripts/verify_reproducibility.py`: checksum, data-manifest, and scientific-claim verification.
- `manuscript/`: anonymous manuscript sources, PDFs, SVG figures, and CSV tables.
- `data_manifest/allen_assets.csv`: source identifiers and URLs for the 40 Allen assets used.
- `reports/`: machine-readable benchmark results and numerical-consistency evidence.

## Data, license, and citation

Project-authored software and documentation are distributed under the MIT License. Allen NWB files,
model configurations, fits, morphologies, mechanisms, and third-party binaries are not included.
They must be retrieved from their original URLs using `data_manifest/allen_assets.csv`; upstream
terms and citation requirements remain applicable. The package verifies the included publication
outputs but does not reproduce the complete Allen-data workflow from source payloads.

Software citation metadata are in [CITATION.cff](CITATION.cff). The
[Zenodo concept DOI](https://doi.org/10.5281/zenodo.21483417) resolves to the latest release; cite
the version-specific DOI associated with the exact software version used for an analysis.
