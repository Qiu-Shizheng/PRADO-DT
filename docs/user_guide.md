# Reference training runner and optional neural modules

This guide covers the reference experiment runner and optional PyTorch modules. For the fitted PRADO models and source-context reliability training, start with the [response-transfer guide](response_transfer.md).

## 1. Installation choices

The core feature map and CPU reference regressor use only the Python standard library. Install the package in editable mode for development:

```bash
python -m pip install -e .
```

For H5AD input, install:

```bash
python -m pip install -e ".[data]"
```

For the neural modules, install a PyTorch build appropriate for the host:

```bash
python -m pip install -e ".[torch]"
```

On a CUDA system, install PyTorch from the command recommended for that CUDA version, then install PRADO-DT with `--no-deps` if you want to keep the environment solver from replacing the existing PyTorch build.

## 2. Input contract

The H5AD reader expects:

- `adata.X`: a numeric cells-by-genes matrix;
- `adata.obs`: one row per cell with a perturbation label and environment label;
- optional drug, dose and time columns;
- control rows that identify the untreated context.

The reader accepts the aliases listed in the main README. If a column has an unusual name, provide an explicit `--*-col` argument.

Expression preprocessing is dataset-specific. The runner does not normalize, log-transform, select highly variable genes or harmonize gene identifiers. Apply those steps before running the model and record the exact gene order. Every row must use the same gene axis.

### Control rows

A control row is a non-targeting or vehicle condition at zero dose. The reader recognizes labels beginning with `NTC` and the labels `control`, `ctrl`, `vehicle`, `none`, `non-targeting`, `non-targeting-grna` and `random_region`. If no control profile is available for an environment, the run stops rather than substituting a treated profile.

Target treated rows are retained for the final score only. The untreated profile itself is computed from control rows and attached to every row from that environment.

### Dose and time

Dose is treated as a non-negative numeric coordinate and transformed with `log1p` in the continuous feature map. Time is numeric and is represented in the condition encoder as a relative exposure coordinate. Do not mix nanomolar, micromolar and arbitrary screen units without a documented conversion.

## 3. CPU reference experiment

Use a small smoke run first:

```bash
python scripts/run_experiment.py --synthetic \
  --seed 7 --genes 4 --perturbations 3 --drugs 2 \
  --cells-per-condition 1 --epochs 2 --out runs/smoke
```

Then inspect:

```bash
cat runs/smoke/metrics.json
cat runs/smoke/config.json
```

For a real H5AD:

```bash
python scripts/run_experiment.py \
  --h5ad /path/to/screen.h5ad \
  --held-out-cell-line target_line \
  --max-cells 100000 --max-genes 512 \
  --seed 7 --out runs/target_line
```

The split is a simple held-out-environment evaluation. For a publication benchmark, reserve a source calibration environment and a separate selection environment before opening the final test labels. The reference CLI does not automate every study-specific split policy.

## 4. Understanding the metrics

`baseline_mse` is the reference feature model without the context-conditioned feature block. `proposed_mse` is the PRADO-DT reference model with untreated context and dose/time features. `proposed_pearson` is the mean per-gene Pearson correlation across evaluation rows. `source_radius_90` is the 90th-percentile absolute residual on source rows. `test_interval_coverage` is the fraction of held-out expression entries inside that transferred interval.

Use MSE and treatment-contrast MSE as separate estimands when studying perturbation effects. A low absolute-expression error can coexist with a weak treatment-effect error when the untreated context explains most of the variance.

## 5. Optional PyTorch modules

`prado_dt.torch_model` provides:

- `PRADODTModel`: dense context-conditioned response head;
- `InvariantResidualModel`: residual response ablation;
- `LowRankInteractionModel`: low-rank gene-by-condition interaction;
- `MixtureResponseModel`: small mixture head for heterogeneous responses.

The models are building blocks rather than a dataset-specific training pipeline. A training loop should:

1. fit only on source environments;
2. construct target context from untreated controls;
3. reserve an independent source environment for model selection and calibration;
4. open treated target rows only for final evaluation;
5. compare against a drug–dose prior on exactly the same rows and genes.

## 6. Reproducibility checklist

Record the following with every analysis:

- data accession and file checksum;
- preprocessing, gene order and number of genes;
- perturbation, drug, dose, time and environment column names;
- control-label rule and number of control rows per environment;
- source, calibration, selection and test environments;
- random seed and maximum cell count;
- software versions and PyTorch/CUDA version when applicable;
- metrics, configuration and split manifests.

The reference regressor uses a local seeded random generator. GPU training can still vary across hardware and CUDA kernels; use deterministic PyTorch settings when exact replay is required.

## 7. Troubleshooting

**`No untreated control profile`**: verify the control label, zero-dose encoding and environment column. Use `--include-unmatched` only when unmatched perturbation metadata has been reviewed.

**`H5AD mode requires`**: install the data extra with `python -m pip install -e ".[data]"`.

**Unexpectedly large errors**: verify that expression values are on the same scale, dose units are consistent and the gene axis has not been reordered between train and test data.

**CUDA or PyTorch import errors**: run the CPU reference first. Install a PyTorch wheel compatible with the host driver, and keep the optional neural module separate from the dependency-light core.

**No improvement over the prior**: this is a valid outcome. The transferable prior is the main comparator; a context residual should be retained only when it improves a predeclared source validation environment without using test labels.
