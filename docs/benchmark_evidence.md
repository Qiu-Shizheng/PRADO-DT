# Matched benchmark evidence

The OP3 task predicts responses to known compounds in myeloid cells using B, T and natural killer cells as sources. The main evaluation pools three donors and contains 127 drugs and 5,317 genes. Untreated target controls are available. Every row below uses the same response profiles, genes and control definitions.

| Predictor | MSE | Mean response Pearson correlation |
|---|---:|---:|
| ContextDose, fixed search | 0.074658 | 0.2240 |
| Compound-only gate, fixed search | 0.075912 | 0.1932 |
| scGPT, frozen complete encoder | 0.078524 | 0.1751 |
| scGPT, complete encoder fine-tuning | 0.077463 | 0.1927 |
| scGPT architecture, random initialisation | 0.077438 | 0.1932 |
| Nicheformer, frozen complete encoder | 0.077321 | 0.1956 |
| Nicheformer, complete encoder fine-tuning | 0.077371 | 0.1947 |
| Nicheformer architecture, random initialisation | 0.077393 | 0.1942 |
| Global response with analytic scaling | 0.077398 | 0.1932 |
| Compound-only gate, extended search | 0.075823 | 0.1932 |
| ContextDose, extended search | 0.074393 | 0.2251 |

## Encoder comparison

Complete pretrained encoders process untreated control pseudobulk profiles. A common response head combines the control representation, compound identity and a shared-source-response skip term. Frozen encoders train only the head. Fine-tuning updates all 12 transformer blocks. Random-initialisation controls use the corresponding full architecture. These are task adaptations of control encoders. They do not reproduce the original authors' native single-cell perturbation benchmarks.

Training duration and response amplitude are selected by leave-one-source-cell-type-out validation. Each neural prediction averages three initialisations. Trained checkpoints are selected from 25, 75 and 150 updates. A zero-update shared-response fallback is evaluated separately. Nicheformer's source validation prefers this fallback when it is eligible, giving MSE 0.077440. The Nicheformer rows in the table show the best trained variant in each family. All 18 trained checkpoints reproduce their saved predictions exactly.

## Donor transfer

A separate evaluation withholds one donor and the myeloid cell type jointly. Source responses use only the other two donors. ContextDose reduces MSE relative to the compound-only gate by 0.15%, 0.12% and 0.32% across 119, 120 and 123 compounds, respectively. Only the third paired 95% interval excludes zero. These folds share training donors and are not independent studies.

## Gene-set responses

Forty-seven Hallmark gene sets contain at least ten genes on the measured panel. Their mean response error is 0.012082 for ContextDose and 0.013088 for the compound-only gate. Mean per-compound correlation across these sets increases from 0.512 to 0.540. Gene sets are retained according to annotation coverage, independently of performance. These scores describe coordinated expression responses, not causal pathway activity.

## Data verification

Reaggregation of the released 298,087 single cells exactly reproduces all 1,813 published pseudobulk count profiles and their cell counts on the evaluation panel. The 21,265-gene original release stores raw counts in `AnnData.raw.X`; `AnnData.X` contains processed expression.

The task is a development evaluation on a public study. It does not establish clinical or unseen-compound performance. Primary data: [OP3 benchmark](https://doi.org/10.52202/079017-0650). Model sources: [scGPT](https://github.com/bowang-lab/scGPT) and [Nicheformer](https://github.com/theislab/nicheformer). Gene sets: [MSigDB Hallmarks](https://doi.org/10.1016/j.cels.2015.12.004).
