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
| ContextDose, gene and programme components | **0.073151** | **0.2517** |

The programme model learns coordinated response patterns inside each source-validation fold. The selected OP3 model has 32 programmes and equal gene and programme contributions. It reduces MSE by 3.52% relative to the extended compound-only gate and by 1.67% relative to the gene-only model. A separately selected low-rank response model gives MSE 0.077050. The trained programme model and a source-only fitting interface are included in this package.

## Encoder comparison

Complete pretrained encoders process untreated control pseudobulk profiles. A common response head combines the control representation, compound identity and a shared-source-response skip term. Frozen encoders train only the head. Fine-tuning updates all 12 transformer blocks. Random-initialisation controls use the corresponding full architecture. These are task adaptations of control encoders. They do not reproduce the original authors' native single-cell perturbation benchmarks.

Training duration and response amplitude are selected by leave-one-source-cell-type-out validation. Each neural prediction averages three initialisations. Trained checkpoints are selected from 25, 75 and 150 updates. A zero-update shared-response fallback is evaluated separately. Nicheformer's source validation prefers this fallback when it is eligible, giving MSE 0.077440. The Nicheformer rows in the table show the best trained variant in each family. All 18 trained checkpoints reproduce their saved predictions exactly.

## Donor transfer

A separate evaluation withholds one donor and the myeloid cell type jointly. Source responses use only the other two donors. Source validation also withholds one donor and one source cell type, giving six validation folds. Conditions require complete support in the source donor–cell-type groups.

| Held-out donor | Conditions | Gene and programme MSE | Compound-only MSE |
|---|---:|---:|---:|
| First | 107 | 0.130812 | 0.131768 |
| Second | 115 | 0.123658 | 0.124374 |
| Third | 116 | 0.155570 | 0.155762 |

Only the first paired 95% interval excludes zero. Cell-type-only source validation gives mixed programme-model results. The two validation designs have different source-complete condition sets, so their absolute scores cannot isolate the effect of validation alone. These folds share training donors and are not independent studies.

## Gene-set responses

Forty-seven Hallmark gene sets contain at least ten genes on the measured panel. Their mean response error is 0.010078 for the programme model, 0.012649 for the extended compound-only gate and 0.011931 for the gene-only gate. This is a 20.3% reduction relative to compound-only weighting. The paired difference is −0.002571, with a 95% compound-bootstrap interval from −0.003886 to −0.001406. Mean per-compound correlation across these sets increases from 0.512 to 0.544. Gene sets are retained according to annotation coverage, independently of performance. These scores describe coordinated expression responses, not causal pathway activity.

## Independent interferon-response study

The [Kang study](https://doi.org/10.1038/nbt.4042) measures matched untreated and interferon-beta-stimulated immune cells from eight donors. Published singlet labels and fixed quality criteria retain 23,981 cells. Each fold excludes the evaluation donor's stimulated cells and all stimulated monocytes. B, CD4 T, CD8 T and natural killer cells from the other seven donors provide source responses. Untreated target monocytes remain available. The 2,000-gene panel is selected from source controls separately in each fold.

ContextDose uses the gene-gate parameters fixed in the OP3 extended search, with source effects estimated within the new study. This tests transfer of weighting parameters for a known stimulus. The programme search selects the gene-only option in this single-stimulus setting. Both fixed OP3 recipes and all source-selected variants are retained in the accompanying result table.

| Predictor | CD14 monocyte MSE | CD16 monocyte MSE | CD14 response Pearson | CD16 response Pearson |
|---|---:|---:|---:|---:|
| ContextDose, fixed extended OP3 parameters | **0.051356** | 0.042364 | 0.789 | 0.777 |
| Compound-only gate | 0.052678 | 0.042690 | 0.788 | 0.777 |
| Source mean | 0.054077 | 0.043450 | 0.788 | 0.777 |
| scGen | 0.055909 | 0.040419 | **0.808** | 0.809 |
| scVIDR | 0.053375 | **0.038652** | 0.804 | **0.809** |

[scGen](https://github.com/theislab/scgen) and [scVIDR](https://github.com/BhattacharyaLab/scVIDR) use their native variational architectures and objectives: two 800-unit hidden layers, 100 latent coordinates, at most 100 epochs, and source-only validation. Each family has eight donor folds and three initialisations, giving 48 completed fits. All checkpoint reloads reproduce predictions exactly. Mean-response scores use the three-fit ensemble. Distribution scores average individual fits.

ContextDose has lower CD14 MSE than scGen, with a paired donor-bootstrap difference of −0.004553 (95% interval −0.006480 to −0.002210). The difference against scVIDR includes zero. scVIDR is more accurate for CD16 MSE and both native models have higher response correlations. ContextDose has lower squared MMD than both native models in both populations under the declared source-PCA distribution metric. All 42 Hallmark sets meeting coverage requirements in every fold are included.

The eight donor folds share source training donors. Treatment and control were sequenced in separate lanes in the original study. [Complete mean scores](benchmarks/ifnb_summary.tsv), [donor scores](benchmarks/ifnb_donor_results.tsv), [initialisation results](benchmarks/ifnb_native_seed_results.tsv) and [paired intervals](benchmarks/ifnb_paired_intervals.json) accompany this comparison.

## Data verification

Reaggregation of the released 298,087 single cells exactly reproduces all 1,813 published pseudobulk count profiles and their cell counts on the evaluation panel. The 21,265-gene original release stores raw counts in `AnnData.raw.X`; `AnnData.X` contains processed expression.

The task is a development evaluation on a public study. It does not establish clinical or unseen-compound performance. Primary data: [OP3 benchmark](https://doi.org/10.52202/079017-0650). Model sources: [scGPT](https://github.com/bowang-lab/scGPT) and [Nicheformer](https://github.com/theislab/nicheformer). Gene sets: [MSigDB Hallmarks](https://doi.org/10.1016/j.cels.2015.12.004).
