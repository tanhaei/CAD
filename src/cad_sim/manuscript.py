"""Render shared result values and audit a manuscript's local references.

No fallback numbers, fault-injection claims, or empirical-validation statements
are generated. V3 supplies the prose; this module supplies computed values.
"""
from pathlib import Path
import json
import re
import pandas as pd

from .scoring import LINK_DELETION, LINK_RECOVERY


def latex_text(value: object) -> str:
    replacements = {"\\": r"\textbackslash{}", "_": r"\_", "%": r"\%", "&": r"\&", "#": r"\#", "{": r"\{", "}": r"\}"}
    return "".join(replacements.get(c, c) for c in str(value))


def render_results(results_dir: str | Path) -> str:
    root = Path(results_dir)
    methods = pd.read_csv(root / "method_summary.csv").set_index("method")
    runtime = pd.read_csv(root / "runtime_summary.csv").set_index("method")
    ablation = pd.read_csv(root / "ablation_summary.csv")
    density = pd.read_csv(root / "density_ablation_summary.csv")
    sensitivity = pd.read_csv(root / "sensitivity_summary.csv")
    meta = json.loads((root / "metadata.json").read_text())
    macros = {}
    for method, stem in (("Full CAD", "Full"), ("Unweighted process-aware", "Unweighted")):
        for column, suffix in (("p_at_10", "P"), ("r_at_10", "R"), ("map", "MAP"), ("mrr", "MRR")):
            macros["CAD" + stem + suffix] = f"{methods.loc[method, column]:.2f}"
    for configuration, stem in (("Full CAD", "DensityFull"), ("CAD without recent defect density", "DensityExcluded")):
        row = density.set_index("configuration").loc[configuration]
        for column, suffix in (("p_at_10", "P"), ("r_at_10", "R"), ("map", "MAP"), ("top10_stability", "Stability")):
            macros["CAD" + stem + suffix] = f"{row[column]:.3f}"
    macros["CADWallTime"] = f"{meta['end_to_end_wall_clock_seconds']:.2f}"
    macros["CADAnalysisTime"] = f"{meta['analysis_wall_clock_seconds']:.2f}"
    macros["CADMemory"] = f"{meta['peak_process_memory_mb']:.2f}"
    macros["CADPlatform"] = latex_text(meta["platform"])
    macros["CADPython"] = latex_text(meta["python"])
    macros["CADCPUs"] = str(meta["logical_cpu_count"])
    for method, stem in (("Static fragility", "Static"), ("Frequency only", "Frequency"), ("Unweighted process-aware", "Process"), ("Full CAD", "Full")):
        macros["CADRuntime" + stem] = f"{runtime.loc[method, 'mean_seconds']:.4f}"
    coverage = meta["realized_trace_coverage_mean"]
    for state, stem in (("complete", "Complete"), ("partial", "Partial"), ("unmapped", "Unmapped")):
        macros["CADCoverage" + stem] = f"{100*coverage[state]:.2f}"
    method_rows = []
    for name, row in methods.iterrows():
        cells = [r"Full \CAD" if name == "Full CAD" else latex_text(name)]
        for metric in ("p_at_10", "r_at_10", "map"):
            cells.append(f"{row[metric]:.2f} [{row[metric+'_ci_low']:.2f}, {row[metric+'_ci_high']:.2f}]")
        cells += [f"{row['mrr']:.2f}", f"{runtime.loc[name, 'mean_seconds']:.4f}",
                  "Reference" if name == "Full CAD" else f"{row['cliffs_delta']:.2f} ({latex_text(row['cliffs_delta_label'])})"]
        method_rows.append(" & ".join(cells) + r" \\")
    macros["CADMethodsRows"] = "\n".join(method_rows)
    for frame, key, digits in ((ablation, "CADAblationRows", 2), (density, "CADDensityRows", 3)):
        rows = []
        for _, row in frame.iterrows():
            name = {"Full CAD": r"Full \CAD", "CAD without recent defect density": r"\CAD without defect density", "Static fragility without recent defect density": "Static fragility without defect density"}.get(row["configuration"], latex_text(row["configuration"]))
            cells = [name] + [f"{row[k]:.{digits}f}" for k in ("p_at_10", "r_at_10", "map", "top10_stability")]
            rows.append(" & ".join(cells) + r" \\")
        macros[key] = "\n".join(rows)
    rows = []
    for _, row in sensitivity.iterrows():
        name = {LINK_DELETION: r"Independent deletion of observed links ($p=0.20$)", LINK_RECOVERY: r"Oracle recovery of missing true links ($p=0.20$)"}.get(row["perturbation"], latex_text(row["perturbation"]))
        rows.append(f"{name} & {row['top10_overlap']:.2f}/10 & {row['spearman_rho']:.3f} & {row['kendall_tau']:.3f} " + r"\\")
    macros["CADSensitivityRows"] = "\n".join(rows)
    return "% Generated from CSV/JSON results; do not edit numeric values manually.\n" + "\n".join("\\newcommand{\\" + k + "}{" + v + "}" for k, v in macros.items()) + "\n"


def write_manuscript_results(results_dir: str | Path) -> Path:
    path = Path(results_dir) / "manuscript_results.tex"
    path.write_text(render_results(results_dir))
    return path


def audit_manuscript(path: str | Path) -> dict:
    path = Path(path)
    text = path.read_text()
    labels = re.findall(r"\\label\{([^}]+)\}", text)
    refs = re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", text)
    missing = set(refs) - set(labels)
    if missing or len(labels) != len(set(labels)):
        raise ValueError(f"invalid reference labels: {missing}")
    objects = [x for x in labels if x.startswith(("tab:", "fig:"))]
    unreferenced = set(objects) - set(refs)
    if unreferenced:
        raise ValueError(f"unreferenced tables or figures: {unreferenced}")
    assets = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text)
    inputs = re.findall(r"\\input\{([^}]+)\}", text)
    for name in assets + inputs:
        if not (path.parent / name).is_file():
            raise ValueError(f"missing manuscript input: {name}")
    bib_names = re.findall(r"\\bibliography\{([^}]+)\}", text)
    bib_text = "\n".join((path.parent / (x + ".bib")).read_text() for group in bib_names for x in group.split(","))
    keys = set(re.findall(r"@\w+\s*\{([^,]+),", bib_text))
    for group in re.findall(r"\\cite\{([^}]+)\}", text):
        if set(group.split(",")) - keys:
            raise ValueError(f"missing bibliography key: {group}")
    if re.search(r"\\AuthorInput\{|\bTBD\b|\bTODO\b|should accompany the revised submission|Any submission of the revised", text):
        raise ValueError("author instructions remain in manuscript prose")
    return {"tables": len([x for x in objects if x.startswith("tab:")]),
            "figures": len([x for x in objects if x.startswith("fig:")]),
            "labels": len(labels), "all_objects_referenced": True}
