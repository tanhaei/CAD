# Changelog

## 0.4.0 - 2026-10-06

- aligned the local package with V3 and documented unresolved target-selection and external-validity limits;
- integrated recent-defect-density exclusion into the main runner and exported run-level and summary results;
- generated manuscript result macros from CSV/JSON, removed obsolete rewriting/fallbacks and stale duplicate result JSON;
- corrected trace perturbation names, unused settings, macOS memory units, and unexposed-label exports;
- added configuration, leakage-separation, diagnostic, CLI and manuscript-contract checks;
- regenerated timings and results, updated metadata/source hashes, docs and version declarations.

## 0.3.0 - 2026-08-14

- synchronized all committed ranking, ablation, sensitivity, confidence-interval, and reference-runtime values with the corrected V2 article;
- replaced the stale, non-standard `manuscript_values.json` artifact with strict `article_values.json` plus a synchronization command;
- removed obsolete manuscript/diagram scripts and contradictory manuscript-asset tests from the reduced release;
- applied the declared component-ID tie breaker consistently to sensitivity rankings;
- added explicit article-contract tests and lazy loading for the optional plotting dependency.

## 0.2.0 - 2026-07-10

- removed outcome-aware score and rank calibration;
- fixed relevance labels before scoring and added deterministic defect-level ground truth;
- added run-level pathway and trace-coverage outputs, ablation/sensitivity summaries, and reproducibility tests.
