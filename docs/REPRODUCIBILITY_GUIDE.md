# Reproducibility

## Lightweight benchmark

The public benchmark requires Python 3.11 or newer and only the Python standard library at runtime.

```text
python -m pip install -e ".[dev]"
python -m pytest
neuronal-model-replay-validation benchmark --output benchmark.json
```

The expected benchmark contains 25 method-waveform results and three configurations that meet all
five waveform criteria: fixed-step boundary sampling at 0.005 and 0.0025 ms and the event-timed
reference. Scientific JSON output is RFC 8259 compliant, key-sorted, and excludes run-specific
timing and interpreter metadata so identical inputs produce identical bytes.

## Package verification

From an unchanged release directory:

```text
python scripts/verify_reproducibility.py
```

This verifies every entry in `PUBLIC_RELEASE_SHA256.csv`, the 40-row Allen asset manifest, and 25
numerical and manuscript-claim checks. The default invocation is read-only. To run only the
scientific checks in the private source checkout:

```text
python scripts/verify_reproducibility.py --science-only
```

Use `--report PATH` to write a fresh Markdown report outside the unchanged release directory.

## External data retrieval

`data_manifest/allen_assets.csv` contains direct source URLs for six recordings, six GLIF
configurations, six morphologies, six perisomatic fit files, and sixteen shared mechanism sources.
For each required asset:

1. Retrieve `source_url` into a non-repository data directory.
2. Calculate SHA-256 for rows with a recorded digest.
3. Compare the complete lowercase digest and stop on any mismatch.

Recording digests are supplied for all six NWB files. No Allen payload or compiled third-party
binary is redistributed.

## Supported reproduction boundary

| Operation | Public release status |
|---|---|
| Run the five-waveform synthetic benchmark | Supported |
| Run unit and publication-consistency tests | Supported |
| Verify included files, tables, and manuscript claims | Supported |
| Inspect anonymous manuscript PDFs, SVG figures, and CSV tables | Supported |
| Retrieve upstream assets by identifier and URL | Metadata supplied |
| Regenerate figures and tables from Allen payloads | Not supplied by this lean release |
| Rerun the complete GLIF and perisomatic workflow | Not demonstrated from a fresh public environment |
| Apply constructive playback methods to the 24 perisomatic cases | Not performed |

The scientific simulations used Python 3.11.15, NEURON 8.2.7 at commit `34cf696c4`, AllenSDK
2.16.2, NumPy 1.23.5, GCC 14.3.0, Ubuntu 26.04, and GLIBC 2.43. These identities document the
scientific execution; they are not runtime requirements for the lightweight package.
