import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from prado_dt.core import LinearRegressor, condition_features


class PradoDTTests(unittest.TestCase):
    def test_condition_features_are_finite(self):
        values = condition_features(2, 4, 1.0, 24.0, drug=1, n_drugs=2)
        self.assertTrue(values)
        self.assertTrue(all(abs(value) < 1e6 for value in values))

    def test_regressor_seed_is_reproducible(self):
        x = [[0.0], [1.0], [2.0], [3.0]]
        y = [[0.0], [1.0], [2.0], [3.0]]
        a = LinearRegressor(1, 1, epochs=3, seed=7)
        b = LinearRegressor(1, 1, epochs=3, seed=7)
        a.fit(x, y); b.fit(x, y)
        self.assertEqual(a.predict_one([1.5]), b.predict_one([1.5]))

    def test_cli_smoke(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "run"
            subprocess.run([
                sys.executable, "scripts/run_experiment.py", "--synthetic",
                "--genes", "2", "--perturbations", "2", "--drugs", "1",
                "--cells-per-condition", "1", "--epochs", "1", "--out", str(out),
            ], check=True, stdout=subprocess.PIPE, text=True)
            metrics = json.loads((out / "metrics.json").read_text())
            self.assertEqual(metrics["model"], "PRADO-DT")
            self.assertGreater(metrics["n_test"], 0)


if __name__ == "__main__":
    unittest.main()
