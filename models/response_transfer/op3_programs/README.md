# Gene and programme response transfer

This ContextDose model combines gene-level reliability with coordinated response programmes learned from B, T and natural killer cells in the OP3 screen. It predicts the listed 127 drug conditions on 5,317 genes.

Supply an untreated target profile transformed to log1p counts per million across the released gene panel. Gene identities must match the model exactly. The target control supplies the expression background. The model supplies the predicted treatment-induced change.

```bash
contextdose-predict \
  --model-dir models/response_transfer/op3_programs \
  --control models/response_transfer/op3_programs/example_control.csv \
  --conditions models/response_transfer/op3_programs/example_conditions.csv \
  --output predictions.npz
```

Source validation selects 32 response programmes and equal weights for the gene and programme branches, followed by a shared amplitude calibration. The model gives MSE 0.073151 and mean response Pearson correlation 0.252 on pooled myeloid responses from the same three donors. This evaluates cell-type transfer for known drugs, doses and exposure times.

The model arrays contain source effect moments, the orthonormal programme basis and programme-coordinate moments. They contain no individual-cell observations. `source_validation.json` records source-only model selection. `verification.json` records replay through the public prediction API.

See the [benchmark guide](../../../docs/benchmark_evidence.md) for matched comparisons and donor-transfer results.
