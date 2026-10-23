# Response-transfer model guide

The fitted models estimate a response shared across source cell types and attenuate effects that disagree between those sources. A compound-level factor describes overall consistency. A gene-level factor describes consistency at each response gene. Source-context validation determines their mixture and scale.

## Preparing effects for training

Use matched untreated controls within the relevant donor, cell type and experimental batch. Form one response vector per condition and source context. Keep drug identity, physical concentration and exposure time explicit. All source contexts in a training array must have the same condition and gene ordering.

Use at least three source contexts. The model fits shared effects on all supplied sources after selecting parameters by leave-one-source-context-out validation. All 65 candidate configurations are reported in `source_validation.json`. The objective averages each held-out source MSE after division by its no-effect MSE.

`fit_from_arrays(effects)` in `prado_dt.transfer_fit` returns mean effects, between-context variance of the mean, selected parameters and validation scores. The command-line interface also writes the metadata needed by `contextdose-predict`.

## Expression scales

**OP3:** sum counts for each eligible cell-type, donor and library profile, then use log1p CPM across the 5,317 released genes. The fitted study uses profiles with at least 20 cells and matched library controls. Source and target cell types share donors.

**Cellarity:** use the released 13,290-gene processed expression scale. The fitted study matches each treated profile to the same cell type and experimental library before averaging response profiles. The public release reuses row labels, so identify samples by cell type, library and well.

A new dataset with matching gene names may have a different measurement scale. Fit a model with compatible source data when the transformation or gene panel differs.

## Population comparison

All rows compare the hierarchical compound–gene gate with the independently selected compound-only gate on identical profiles.

| Population | Conditions | Hierarchical MSE | Compound-only MSE | Hierarchical response r | Compound-only response r |
|---|---:|---:|---:|---:|---:|
| Cellarity CD34+ progenitors | 44 | 0.028974 | 0.029018 | 0.216 | 0.210 |
| Cellarity CD8+ T cells | 4 | 0.014900 | 0.014583 | 0.294 | 0.293 |
| Cellarity airway epithelial cells | 44 | 0.046470 | 0.046657 | 0.213 | 0.211 |
| Cellarity preadipocytes | 44 | 0.034064 | 0.034076 | 0.214 | 0.210 |
| OP3 myeloid cells, pooled donors | 127 | 0.074658 | 0.075912 | 0.224 | 0.193 |

The OP3 paired MSE difference is −0.001253, with a 95% compound-cluster bootstrap interval of [−0.001590, −0.000930]. Donor-stratified comparisons agree in direction and reuse observations from the pooled analysis. Removing the across-compound mean of each gene gives response correlations of 0.231 and 0.201 for hierarchical and compound-only weighting, respectively.

These are development evaluations with models fitted separately within each study. The tested conditions concern known drugs at supported doses and times. The available data do not establish unseen-drug, new-study or clinical predictive performance.

## Model files

### Extended source search

The optional `op3_refined` checkpoint uses the same prediction equation with a broader source-only search. The reliability penalty spans 0.001 to 1,000, with a zero-penalty candidate. Nine compound/gene mixtures are tested. Each candidate's response scale is fitted analytically on source validation folds, within [0, 2]. The resulting 442 candidates require no target response profiles.

```bash
contextdose-fit \
  --source-effects source_effects.npz \
  --input-scale log1p_cpm \
  --search extended \
  --output fitted_extended_model
```

Use `models/response_transfer/op3_refined` as the model directory for the supplied refined checkpoint. Its input contract matches the original OP3 checkpoint. The Python API accepts `fit_from_arrays(effects, search="extended")`. The default `standard` search reproduces the original model.

- `model.npz`: shared effects and between-source variance of their mean.
- `model.json`: gene identities, physical treatment conditions and selected parameters.
- `example_control.csv`: a source control for checking the input format.
- `example_conditions.csv`: three supported treatment conditions.
- `../verification.json`: numerical replay checks for the frozen evaluation groups.

The core glioblastoma expression model uses a separate predictor and released dose-level codes. Its dose codes must not be substituted for the physical concentrations used by these response-transfer models.
