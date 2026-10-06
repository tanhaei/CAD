# Local validation report — 6 October 2026

The directory named `git` has no `.git` checkout metadata. Tests and revisions are local; no remote publication was performed.

## Full synthetic experiment

`python scripts/run_experiment.py --config config/synthetic_experiment.json --output-dir results` completed 30 runs, seeds 42–71, with 10,000 run-level BCa resamples. It regenerated method/factor/density/sensitivity outputs and manuscript macros. Full CAD P@10=0.9866666667, MAP=0.9604650838; density-excluded CAD P@10=0.9366666667, MAP=0.9411918547. Source hashes in metadata match the final package files. The count total 500,000 is multinomial count mass, not individually processed events.

Measured environment: macOS-27.0.1-arm64-arm-64bit-Mach-O; Python 3.13.16; 10 logical CPUs. In-process wall time through initial result serialization 0.513586 s; peak process memory 125.796875 MB. Post-measurement snapshot/macro refresh and stdout printing are excluded. Timings are environment-dependent, not production scalability evidence.

## Tests and commands

`python -m pytest -q`: **46 passed**. Tests include score arithmetic, rank/metric boundaries, deterministic retrieval, label/multiplicity separation, density renormalization and input preservation, invalid configuration, strict JSON, CLI output consistency, manuscript contracts, CSV key/date validation, preserved source bytes, and exclusion of incident pathway/effort fields from historical scoring.

The script CLI and installed `cad-sim --quick` entry point passed. Synchronization and V3 updater commands passed. `compileall` and shell syntax checking passed. Optional plotting generated four PDF/PNG pairs from an actual three-run profile; operating points are not invented precision–recall curves. The `uv` installation workflow and the remote CI were not executed.

## Supplied data audit

`python scripts/audit_data.py --data-dir ../data --output-dir results/data_audit` passed. The five CSVs contain 45 components, 437 edges, a 45×45 matrix, 45 T1 rows and 120 T2 incident rows. Edges match the matrix; catalog Ca differs for 41 components and Ce agrees. Supplied fragility differs from recomputation by at most 0.000065, within combined four-decimal rounding. Declared T1/T2 windows are separated and timestamps lie within T2.

One static ranking against T2 labels gives P@10=0.100, R@10=0.0833333333, AP=0.2269618213. These are separate descriptive results; full CAD is unavailable without historical pathway/criticality/trace inputs. T2 per-component incident counts equal the original synthetic label-count vector, so extraction/selection history must establish independence before an independent replication claim. Attribution and exclusion flags alone do not verify provenance. Source CSVs were preserved.

## Manuscript and response

V3 has 10 tables and 4 figures; all are referenced in prose. Inputs and bibliography keys pass the source audit. Local TeX Live compiles V3, the response and exact guide; PDF rendering provides visual checks. The desktop compiler was attempted but could not obtain a required font/bundle resource. Local compilation is the verified PDF output path.

Evidence logs are under `../reviewer-revision/integrity-audit/`. Reproducibility and presentation checks do not resolve historical target selection, operational measurement provenance, process mining, real trace alignment, maintenance benefit, or generalizability.

## Final editorial verification (6 October 2026)

After the final 26 article edits, `python -m pytest -q` again passed all 46 tests. The final audit independently verifies prose references for all 10 tables and 4 figures, exact edit replay, generated values, package-source hashes and unchanged raw CSV hashes. Article results were not regenerated in this editorial pass because computation and data were unchanged. Local article compilation and PDF inspection succeeded; the native editor does not support its external relative inputs. The standalone final guide and response compiled successfully in the native editor. Evidence is in `../reviewer-revision/integrity-review-final/`.
