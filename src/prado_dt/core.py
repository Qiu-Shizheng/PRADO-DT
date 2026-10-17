"""PRADO-DT core feature maps and a dependency-free reference regressor.

The reference implementation is intentionally small and transparent. It
mirrors the interface used by an optional frozen transcriptome encoder:
baseline cell state, perturbation identity, drug/environment identity, dose,
time and a control-derived cell-line context profile.
"""

from __future__ import division

import json
import math
import random


def _safe_log(x):
    return math.log(max(float(x), 1e-8))


def fourier(value, n=3):
    """Stable Fourier features for a positive continuous condition."""
    z = _safe_log(value)
    out = [z]
    for k in range(1, n + 1):
        out.extend([math.sin(k * z), math.cos(k * z)])
    return out


def condition_features(perturbation, n_perturbations, dose, time,
                       drug=0, n_drugs=1, n_fourier=2):
    p = [0.0] * n_perturbations
    p[int(perturbation) % n_perturbations] = 1.0
    ddrug = [0.0] * max(1, n_drugs)
    ddrug[int(drug) % max(1, n_drugs)] = 1.0
    d = fourier(dose, n_fourier)
    t = fourier(time, n_fourier)
    dynamic = [float(time), math.exp(-float(time) / 24.0), float(dose),
               float(dose) * float(time)]
    return p + ddrug + d + t + dynamic


def feature_map(row, n_perturbations, n_drugs=1, context_profiles=None,
                proposed=False):
    """Map one row to a deterministic real-valued feature vector."""
    x = list(row["baseline"])
    drug = row.get("drug", 0)
    if not proposed:
        # Static baseline: categorical perturbation and one dose scalar;
        # exposure time and cell-line context are intentionally ignored.
        base = x + condition_features(row["perturbation"], n_perturbations,
                                      row["dose"], 1.0, drug, n_drugs,
                                      n_fourier=0)
        base.append(float(row["dose"]))
        return base
    base = x + condition_features(row["perturbation"], n_perturbations,
                                  row["dose"], row["time"], drug, n_drugs)
    profile = []
    if context_profiles is not None:
        profile = list(context_profiles.get(str(row["cell_line"]), []))
    if not profile:
        profile = [0.0] * len(x)
    # Context-conditioned interaction is low-rank in the neural version; this
    # explicit product is the auditable reference form.
    interaction = [a * b for a, b in zip(profile, x)]
    return base + profile + interaction


class LinearRegressor(object):
    """Tiny SGD ridge regressor supporting multi-output responses."""

    def __init__(self, n_features, n_outputs, lr=0.01, l2=1e-4, epochs=30,
                 seed=0):
        self.n_features = n_features
        self.n_outputs = n_outputs
        self.lr = lr
        self.l2 = l2
        self.epochs = epochs
        rng = random.Random(seed)
        self.w = [[rng.uniform(-0.01, 0.01) for _ in range(n_outputs)]
                  for _ in range(n_features)]
        self.b = [0.0] * n_outputs
        self.scales = [1.0] * n_features
        self._rng = random.Random(seed + 1000003)

    def predict_one(self, x):
        return [self.b[j] + sum((x[i] / self.scales[i]) * self.w[i][j]
                                for i in range(self.n_features))
                for j in range(self.n_outputs)]

    def fit(self, xs, ys, shuffle=True):
        # RMS normalization keeps dose*time and Fourier features numerically
        # comparable to gene-state features in the dependency-free path.
        self.scales = []
        for i in range(self.n_features):
            rms = math.sqrt(sum(x[i] * x[i] for x in xs) / max(1, len(xs)))
            self.scales.append(max(1.0, rms))
        order = list(range(len(xs)))
        for _ in range(self.epochs):
            if shuffle:
                self._rng.shuffle(order)
            for idx in order:
                x, y = xs[idx], ys[idx]
                pred = self.predict_one(x)
                err = [pred[j] - y[j] for j in range(self.n_outputs)]
                scale = 2.0 / max(1, self.n_outputs)
                for i, raw_xi in enumerate(x):
                    xi = raw_xi / self.scales[i]
                    if xi == 0.0:
                        continue
                    wi = self.w[i]
                    for j in range(self.n_outputs):
                        wi[j] -= self.lr * (scale * xi * err[j] + self.l2 * wi[j])
                for j in range(self.n_outputs):
                    self.b[j] -= self.lr * scale * err[j]


def mse(pred, true):
    n = max(1, len(pred) * len(pred[0]))
    return sum((a - b) ** 2 for p, q in zip(pred, true)
               for a, b in zip(p, q)) / n


def pearson_rows(pred, true):
    """Mean per-output Pearson correlation without external dependencies."""
    if not pred:
        return 0.0
    values = []
    for j in range(len(pred[0])):
        a = [p[j] for p in pred]
        b = [q[j] for q in true]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        va = sum((v - ma) ** 2 for v in a)
        vb = sum((v - mb) ** 2 for v in b)
        if va <= 1e-12 or vb <= 1e-12:
            continue
        values.append(sum((u - ma) * (v - mb) for u, v in zip(a, b)) /
                     math.sqrt(va * vb))
    return sum(values) / max(1, len(values))


def conformal_radius(pred, true, alpha=0.1):
    residuals = sorted(abs(a - b) for p, q in zip(pred, true)
                       for a, b in zip(p, q))
    if not residuals:
        return 0.0
    index = min(len(residuals) - 1,
                int(math.ceil((len(residuals) + 1) * (1.0 - alpha))) - 1)
    return residuals[index]


def save_json(path, obj):
    with open(path, "w") as handle:
        json.dump(obj, handle, indent=2, sort_keys=True)
