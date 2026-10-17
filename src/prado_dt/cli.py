"""Command-line reference runner for PRADO-DT."""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from .core import LinearRegressor, conformal_radius, feature_map, mse, pearson_rows


def synthetic(seed=7, n_genes=8, n_perts=4, n_drugs=2, cells_per_condition=2):
    """Create a small deterministic dataset for a CPU smoke test."""
    rng = random.Random(seed)
    lines = ["source_A", "source_B", "held_out"]
    line_effect = {line: [rng.uniform(-0.8, 0.8) for _ in range(n_genes)]
                   for line in lines}
    pert_effect = [[rng.uniform(-1.0, 1.0) for _ in range(n_genes)]
                   for _ in range(n_perts)]
    drug_effect = [[rng.uniform(-1.0, 1.0) for _ in range(n_genes)]
                   for _ in range(n_drugs)]
    rows = []
    for line in lines:
        context = [1.0 + v for v in line_effect[line]]
        for pert in range(n_perts):
            for drug in range(n_drugs):
                for dose in (0.25, 1.0, 4.0):
                    for time in (6.0, 24.0):
                        for _ in range(cells_per_condition):
                            baseline = [context[g] + rng.gauss(0.0, 0.15)
                                        for g in range(n_genes)]
                            d = math.log1p(dose)
                            t = 1.0 - math.exp(-time / 18.0)
                            target = []
                            for g in range(n_genes):
                                response = (pert_effect[pert][g] + drug_effect[drug][g]) * d * t
                                response *= 1.0 + 0.45 * line_effect[line][g]
                                response += 0.10 * baseline[g]
                                target.append(response + rng.gauss(0.0, 0.08))
                            rows.append({"baseline": baseline, "target": target,
                                         "context_profile": context,
                                         "perturbation": pert, "drug": drug,
                                         "dose": dose, "time": time,
                                         "cell_line": line})
    return rows


def _find_column(obs, explicit, candidates):
    if explicit and explicit in obs.columns:
        return explicit
    return next((name for name in candidates if name in obs.columns), None)


def load_h5ad(path, max_cells=100000, max_genes=512, columns=None,
              include_unmatched=False, seed=7):
    """Load a public H5AD and construct context profiles from controls only."""
    try:
        import anndata
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("H5AD mode requires: pip install 'prado-dt[data]'") from exc
    adata = anndata.read_h5ad(path)
    obs = adata.obs
    columns = columns or {}
    found = {
        "perturbation": _find_column(obs, columns.get("perturbation_col"),
                                      ["perturbation", "perturbation_name", "condition", "gRNA"]),
        "drug": _find_column(obs, columns.get("drug_col"), ["drug", "drug_name", "compound"]),
        "dose": _find_column(obs, columns.get("dose_col"), ["dose", "perturbation_value", "concentration"]),
        "time": _find_column(obs, columns.get("time_col"), ["time", "hours", "perturbation_time"]),
        "cell_line": _find_column(obs, columns.get("cell_line_col"), ["cell_line", "celltype", "cell_type", "line"]),
    }
    if found["perturbation"] is None:
        raise ValueError("No perturbation column found in H5AD observation metadata")
    status_col = next((x for x in ("gRNA_assignment_status", "assignment_status") if x in obs.columns), None)
    n_genes = min(int(max_genes), int(adata.shape[1]))
    def row_vec(i):
        raw = adata.X[i, :n_genes]
        if hasattr(raw, "toarray"):
            raw = raw.toarray()[0]
        return [float(v) for v in np.asarray(raw).reshape(-1)]
    controls = {}
    selected = []
    for i in range(len(obs)):
        if status_col and not include_unmatched:
            status = str(obs.iloc[i][status_col]).strip().lower()
            if status in {"unmatched_public_namespace", "unmatched", "unknown", "ambiguous"}:
                continue
        perturbation = str(obs.iloc[i][found["perturbation"]])
        p_lower = perturbation.strip().lower()
        dose_raw = obs.iloc[i][found["dose"]] if found["dose"] else 1.0
        try:
            dose = float(dose_raw)
        except (TypeError, ValueError):
            dose = 0.0 if p_lower.startswith("ntc") or p_lower in {"control", "vehicle", "ctrl", "non-targeting"} else 1.0
        line = str(obs.iloc[i][found["cell_line"]]) if found["cell_line"] else "unknown"
        control = (p_lower.startswith("ntc") or p_lower in {"control", "ctrl", "vehicle", "none", "non-targeting", "non-targeting-grna", "random_region"}) and dose == 0.0
        if control:
            controls.setdefault(line, []).append(i)
        else:
            selected.append((i, line, perturbation, dose))
    if not selected:
        raise ValueError("No treated rows remain after filtering")
    rng = random.Random(seed)
    rng.shuffle(selected)
    selected = selected[:int(max_cells)]
    profiles = {}
    profile_counts = {}
    for line, ids in controls.items():
        ids = ids[:5000]
        if ids:
            arr = [row_vec(i) for i in ids]
            profiles[line] = [sum(v[g] for v in arr) / len(arr) for g in range(n_genes)]
            profile_counts[line] = len(ids)
    missing = sorted({line for _, line, _, _ in selected} - set(profiles))
    if missing:
        raise ValueError("No untreated control profile for: %s" % ", ".join(missing))
    p_vocab = {p: j for j, p in enumerate(sorted({p for _, _, p, _ in selected}))}
    d_vocab = {"__default__": 0}
    if found["drug"]:
        names = sorted({str(obs.iloc[i][found["drug"]]) for i, _, _, _ in selected})
        d_vocab = {name: j for j, name in enumerate(names)}
    rows = []
    for i, line, perturbation, dose in selected:
        drug_name = str(obs.iloc[i][found["drug"]]) if found["drug"] else "__default__"
        try:
            time = float(obs.iloc[i][found["time"]]) if found["time"] else 1.0
        except (TypeError, ValueError):
            time = 1.0
        rows.append({"baseline": profiles[line], "context_profile": profiles[line],
                     "target": row_vec(i), "perturbation": p_vocab[perturbation],
                     "drug": d_vocab[drug_name], "dose": dose, "time": time,
                     "cell_line": line, "baseline_control_n": profile_counts[line],
                     "perturbation_label": perturbation, "drug_label": drug_name,
                     "row_id": str(obs.index[i])})
    return rows


def _profiles(rows):
    profiles = {}
    for row in rows:
        if "context_profile" in row:
            profiles.setdefault(str(row["cell_line"]), list(row["context_profile"]))
    if profiles:
        return profiles
    sums, counts = {}, {}
    for row in rows:
        line = str(row["cell_line"])
        sums.setdefault(line, [0.0] * len(row["baseline"]))
        counts[line] = counts.get(line, 0) + 1
        for j, value in enumerate(row["baseline"]):
            sums[line][j] += value
    return {line: [v / counts[line] for v in values] for line, values in sums.items()}


def run(args):
    rows = synthetic(args.seed, args.genes, args.perturbations, args.drugs,
                     args.cells_per_condition) if args.synthetic else load_h5ad(
                         args.h5ad, args.max_cells, args.max_genes, vars(args),
                         args.include_unmatched, args.seed)
    lines = sorted({str(row["cell_line"]) for row in rows})
    held = args.held_out_cell_line or lines[-1]
    if held not in lines:
        raise ValueError("Held-out cell line is not present: %s" % held)
    train = [row for row in rows if str(row["cell_line"]) != held]
    test = [row for row in rows if str(row["cell_line"]) == held]
    profiles = _profiles(rows)
    n_perts = max(int(row["perturbation"]) for row in rows) + 1
    n_drugs = max(int(row.get("drug", 0)) for row in rows) + 1
    bx = [feature_map(row, n_perts, n_drugs, profiles, proposed=False) for row in train]
    px = [feature_map(row, n_perts, n_drugs, profiles, proposed=True) for row in train]
    btest = [feature_map(row, n_perts, n_drugs, profiles, proposed=False) for row in test]
    ptest = [feature_map(row, n_perts, n_drugs, profiles, proposed=True) for row in test]
    y_train = [row["target"] for row in train]
    y_test = [row["target"] for row in test]
    baseline = LinearRegressor(len(bx[0]), len(y_train[0]), lr=args.lr, epochs=args.epochs, seed=args.seed)
    proposed = LinearRegressor(len(px[0]), len(y_train[0]), lr=args.lr, epochs=args.epochs, seed=args.seed + 1)
    baseline.fit(bx, y_train)
    proposed.fit(px, y_train)
    bp = [baseline.predict_one(x) for x in btest]
    pp = [proposed.predict_one(x) for x in ptest]
    radius = conformal_radius([proposed.predict_one(x) for x in px], y_train, alpha=0.1)
    coverage = sum(abs(a - b) <= radius for pred, true in zip(pp, y_test) for a, b in zip(pred, true)) / float(max(1, len(pp) * len(pp[0])))
    metrics = {"model": "PRADO-DT", "held_out_cell_line": held,
               "n_train": len(train), "n_test": len(test),
               "baseline_mse": mse(bp, y_test), "proposed_mse": mse(pp, y_test),
               "baseline_pearson": pearson_rows(bp, y_test),
               "proposed_pearson": pearson_rows(pp, y_test),
               "source_radius_90": radius, "test_interval_coverage": coverage,
               "semantics": "reference smoke or H5AD condition-level evaluation; inspect split and controls before scientific use"}
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    (out / "config.json").write_text(json.dumps(vars(args), indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return metrics


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the PRADO-DT CPU reference experiment")
    parser.add_argument("--synthetic", action="store_true", help="use deterministic synthetic data")
    parser.add_argument("--h5ad", help="path to a prepared AnnData H5AD file")
    parser.add_argument("--out", default="runs/smoke")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--genes", type=int, default=8)
    parser.add_argument("--perturbations", type=int, default=4)
    parser.add_argument("--drugs", type=int, default=2)
    parser.add_argument("--cells-per-condition", type=int, default=2)
    parser.add_argument("--held-out-cell-line")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=0.002)
    parser.add_argument("--max-cells", type=int, default=100000)
    parser.add_argument("--max-genes", type=int, default=512)
    parser.add_argument("--include-unmatched", action="store_true")
    for key in ("perturbation", "drug", "dose", "time", "cell_line"):
        parser.add_argument("--%s-col" % key)
    args = parser.parse_args(argv)
    if not args.synthetic and not args.h5ad:
        args.synthetic = True
    run(args)
    return None


if __name__ == "__main__":
    main()
