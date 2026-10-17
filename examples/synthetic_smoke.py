"""Run the smallest reproducible PRADO-DT example."""
from prado_dt.cli import main

if __name__ == "__main__":
    main([
        "--synthetic", "--seed", "7", "--genes", "4",
        "--perturbations", "3", "--drugs", "2",
        "--cells-per-condition", "1", "--epochs", "2",
        "--out", "runs/example",
    ])
