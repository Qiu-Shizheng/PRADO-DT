# scPerturbMix expression model

A frozen, CPU-compatible expression predictor fitted to the glioblastoma gene-by-drug screen. It combines the source expression mean, an untreated target-control adjustment and a drug-dose offset. It predicts 512 gene-expression values per condition.

## Run the example

```bash
python -m pip install -r requirements.txt
python predict.py --control example_control.csv --conditions example_conditions.csv --output predictions.npz
```

The example control is the source untreated profile and illustrates the input format. It is not a new validation experiment.

## Use another control profile

Supply a CSV with `gene_id` and `expression` columns, containing exactly the 512 genes listed in `model.json`. Gene order may differ. Values must use the same expression transformation as the glioblastoma benchmark matrix. The software checks gene identity and rejects nonfinite inputs.

The condition CSV contains unique `condition_id`, `drug` and `dose_level` columns. Supported compounds are lapatinib, nintedanib, trametinib and zstk474. Dose levels 1 and 10 are the released benchmark codes. They are not automatically interpreted as micromolar concentrations. The vehicle condition uses `vehicle,0`. Unsupported conditions raise an error.

The output archive contains `prediction`, `expression_gene_ids` and `condition_id`. The NumPy API is `predict(control, gene_ids, compounds, dose_levels, model_dir=None)`.

## Model scope

The selected model was fitted on A172 conditions and selected using T98G. Its U87MG evaluation is a development analysis. Genetic main effects and interaction terms received zero contribution in validation, so this frozen model does not distinguish genetic targets at the same drug-dose condition. Other scPerturbMix tasks use separately fitted models. This package contains the whole-profile glioblastoma model only.
