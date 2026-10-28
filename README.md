# PRADO

**Single-cell perturbation response modelling**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](pyproject.toml)

PRADO models changes in gene expression caused by chemical, immune and genetic perturbations. It combines gene-level responses with coordinated gene programmes to predict cellular responses under different cell identities, donor backgrounds and treatment conditions. The research evaluation covers drug responses, immune stimulation, dose dependence and genetic interventions.

![PRADO model architecture](docs/architecture.svg)

## How the response model works

The main model uses **statistical machine learning**: it combines shared responses, reliability weighting and a learned low-dimensional representation. Held-out training contexts select how much each component contributes. The released predictor runs on a CPU with NumPy. Optional neural reference code is provided separately.

For each treatment, the model estimates a shared response and measures how consistently that response occurs across source contexts. It combines estimates at the treatment, gene and response-programme levels. A programme is a low-dimensional direction learned from coordinated variation in source responses. Hallmark gene sets are used separately to interpret and evaluate biological responses.

The released response-transfer checkpoints return a treatment-induced change, `effect`, and an absolute expression prediction, `prediction = target_control + effect`. The supplied untreated target profile supplies the final expression baseline. Changing that profile changes the absolute prediction while leaving the core model's treatment effect unchanged. The separately evaluated target-context kernel extension uses untreated cell-state information to change the predicted effect itself. Its study-level analyses are described in the [benchmark guide](docs/benchmark_evidence.md).

See [data and prediction tasks](docs/data_and_tasks.md) for the biological meaning of each dataset, its training and evaluation roles, and the distinction between the released checkpoints and the broader research evaluation.

## Install

The Python package is `prado-dt` (`prado_dt` for imports). Its command-line tools are `contextdose-fit` and `contextdose-predict`.

```bash
git clone https://github.com/Qiu-Shizheng/PRADO-DT.git
cd PRADO-DT
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Predict with a fitted model

```bash
contextdose-predict \
  --model-dir models/response_transfer/op3 \
  --control models/response_transfer/op3/example_control.csv \
  --conditions models/response_transfer/op3/example_conditions.csv \
  --output predictions.npz
```

The example uses a source control to demonstrate the file format. For your experiment, supply an untreated target control on the model's gene axis and expression scale. These checkpoints predict the drug, dose and exposure-time combinations listed in their model files.

| Model | Response genes | Fitting and evaluation setting |
|---|---:|---|
| [OP3 response transfer](models/response_transfer/op3) | 5,317 | B, T and NK source cells; myeloid evaluation from shared donors |
| [OP3 refined response transfer](models/response_transfer/op3_refined) | 5,317 | Wider source-only reliability search with analytic response scaling |
| [OP3 gene and programme model](models/response_transfer/op3_programs) | 5,317 | Parallel gene and learned-programme reliability, with source-only selection |
| [Cellarity response transfer](models/response_transfer/primary) | 13,290 | Six cultured source lines; four primary-cell populations |
| [Glioblastoma expression](models/expression) | 512 | A172 fitting, T98G selection and U87MG development evaluation |

The response-transfer models predict listed drug–dose–time conditions. The expression model has a separate command documented in its [README](models/expression/README.md).

## Input and output

The control CSV contains `gene_id,expression`. All model genes must occur exactly once, in any order. The condition CSV contains:

```csv
condition_id,drug,dose_uM,time_hours
```

Choose supported combinations from the model's `model.json` or copy its example condition file. Doses are in micromolar and exposure times are in hours. The software rejects unsupported conditions and mismatched genes.

The output NumPy archive contains:

| Array | Meaning |
|---|---|
| `prediction` | Predicted expression, conditions × genes |
| `effect` | Predicted change relative to the supplied control |
| `gene_ids` | Gene order of both output matrices |
| `condition_id` | Input condition identifiers |

OP3 inputs use log1p counts per million across the 5,317 released genes. Cellarity inputs use the original released expression scale. See the [model guide](docs/response_transfer.md) for compatible preprocessing and evaluation scope.

## Python API

```python
from prado_dt import predict_response

prediction, effect, output_genes = predict_response(
    control=control_vector,
    gene_ids=gene_ids,
    compounds=compound_names,
    doses_uM=doses,
    times_hours=exposure_times,
    model_dir="models/response_transfer/op3",
)
```

The control may be one gene vector or one vector per condition.

## Fit your own response model

Provide a NumPy archive containing `effects` with shape **source contexts × shared conditions × genes**, plus `gene_ids`, `drug`, `dose_uM` and `time_hours`. Each effect is measured relative to its matched untreated source control. At least three source contexts are required.

```bash
contextdose-fit \
  --source-effects source_effects.npz \
  --input-scale "log1p CPM across the declared gene panel" \
  --output models/my_response_model
```

The fixed search selects the reliability penalty, compound–gene mixture and response scale by leaving out source contexts. It writes the fitted model and all candidate validation scores. Target treated expression is not an input to this interface.

To fit the gene and programme architecture, install its SciPy fitting dependency and select the programme search:

```bash
python -m pip install -e '.[programs]'
contextdose-fit \
  --source-effects source_effects.npz \
  --input-scale "log1p CPM across the declared gene panel" \
  --search programs \
  --output models/my_programme_model
```

The programme basis is learned anew inside each source-validation fold. Selection includes a gene-only option. Saved programme models use the same `contextdose-predict` command and require only NumPy for inference. At inference, the gene panel, expression transformation, drug identity, dose and exposure time must match the fitted model's input contract.

## Research tasks and data

The research evaluation includes **11 experiments from 10 original studies**: 10 are derived from single-cell measurements and one is a bulk RNA-sequencing auxiliary experiment. Most endpoints are average expression responses for a cell population under a defined treatment.

| Task | Datasets | Prediction target |
|---|---|---|
| Drug responses across cell contexts | OP3, Cellarity | Treated myeloid or primary-cell populations |
| Immune responses across donors and cell types | Kang interferon-beta, Parse cytokines, Wood stimulation | Monocyte responses in a held-out donor |
| Dose response | sci-Plex2, sci-Plex3 | Responses at held-out concentrations |
| Genetic perturbations across environments | Glioblastoma kinome screen, PerturbFate, primary CD4 T-cell panel | Responses in a held-out cell background, target-gene group or donor |
| Prediction after a small pilot experiment | Parse, Wood | Remaining stimuli after observing a few target-context responses |

The pilot task reuses two studies. The diffuse midline glioma PLATE-seq screen provides a separate bulk-expression check. sci-Plex2 and sci-Plex3 come from the same original study.

In most external-study evaluations, a model is fitted to permitted source cells from that study and predicts its held-out targets. Transferring a fixed parameter-selection rule still allows source-response coefficients to be fitted in the new study. These roles are recorded in the [dataset guide](docs/data_and_tasks.md) and [downloadable cohort table](docs/data/cohort_roles_20261028.tsv). Immune-stimulation experiments measure cellular responses to immune signals. Clinical treatment outcomes require a separate evaluation design.

## Evaluation

In the OP3 development task, the hierarchical gate has MSE **0.074658** and mean response Pearson correlation **0.224**, compared with **0.075912** and **0.193** for the separately selected compound-only gate. The comparison uses 127 drugs and the same 5,317 response genes. Cellarity effects vary by population. The [model guide](docs/response_transfer.md) reports the complete population comparison and scope.

The optional refined OP3 model has MSE **0.074393** and response correlation **0.225**, compared with **0.075823** for a compound-only model selected using the same wider search. Use `--search extended` with `contextdose-fit` to apply this fitting procedure to your own source profiles. The original model and default search remain available for reproduction.

The gene and programme model has MSE **0.073151** and response correlation **0.252**, a **3.52%** MSE reduction relative to the extended compound-only model on these same conditions. This result evaluates transfer between cell types represented in shared donors. Jointly unseen donors require a separate evaluation design, described in the benchmark guide.

The [matched benchmark evidence](docs/benchmark_evidence.md) includes complete scGPT and Nicheformer encoder adaptations, random-initialisation controls, joint donor/cell-type transfer and gene-set response analysis.

The benchmark guide also includes independent interferon and multi-cytokine studies. The twelve-donor cytokine evaluation covers 2,003 response pairs and identifies a setting where the selected model matches simple global response scaling. Complete model comparisons and donor-level source tables are provided. Compare models within a matched task: gene panels, normalisation, available target information and evaluation units differ between datasets.

Saved models replay the frozen evaluation predictions to numerical precision. Run the software tests with:

```bash
python -m unittest discover -s tests -v
```

For H5AD loading, the synthetic training runner and optional PyTorch modules, see the [reference implementation guide](docs/user_guide.md).

## Data and citation

The repository includes fitted model parameters and example inputs. Obtain experimental expression matrices from the original studies:

- [OP3, NeurIPS 2024](https://doi.org/10.52202/079017-0650)
- [Cellarity compound-response atlas](https://doi.org/10.1126/science.adi8577)

The [dataset guide](docs/data_and_tasks.md) links every study in the research evaluation and explains the analysed subset. See [CITATION.cff](CITATION.cff) to cite the software. Code is distributed under the [MIT License](LICENSE). Original datasets retain their source licences.
