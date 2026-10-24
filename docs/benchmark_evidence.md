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

## Independent multi-cytokine study

The [Parse PBMC cytokine dataset](https://www.parsebiosciences.com/datasets/10-million-human-pbmcs-in-a-single-experiment/) contains 9,697,974 blood immune cells from twelve healthy donors exposed to 90 cytokines and PBS controls. The evaluation predicts CD14 and CD16 monocyte responses from seven B-cell, T-cell and natural-killer-cell populations. Every outer fold excludes stimulated cells from the held-out donor and all stimulated target monocytes. Source controls determine the 2,000-gene panel. Inner validation jointly holds out a donor and source population.

Fixed minimum support of twenty cells in treatment and matched control yields 1,046 CD14 and 957 CD16 donor–cytokine pairs. Scores first average eligible conditions within each donor, then weight the twelve donors equally. All eligible conditions are retained. One donor has only one eligible CD16 condition. The experiment uses one plate per donor, so donor and plate effects are not separately identifiable.

| Predictor | CD14 MSE | CD16 MSE | CD14 response Pearson | CD16 response Pearson |
|---|---:|---:|---:|---:|
| ContextDose, frozen source-selection procedure | 0.011929 | 0.018094 | 0.3963 | 0.3381 |
| Global response scaling | 0.011929 | 0.018094 | 0.3963 | 0.3381 |
| Source mean | 0.012313 | 0.018521 | 0.3963 | 0.3381 |
| Untreated | 0.013759 | 0.020295 | Undefined | Undefined |

The selected model reduces MSE by 3.12% and 2.30% relative to the source mean. All twelve folds select zero programme contribution, and predictions match global scaling to displayed precision. Thus this cohort supports response calibration without establishing an additional programme-model benefit. [All nine frozen comparators and four follow-up variants](benchmarks/parse_model_metrics.tsv) are included, alongside [donor scores](benchmarks/parse_donor_metrics.tsv), [paired intervals](benchmarks/parse_paired_intervals.tsv), [coverage](benchmarks/parse_condition_coverage.tsv) and [all-pair weighting sensitivity](benchmarks/parse_profile_weighted_sensitivity.tsv).

### Cell-state follow-up

A follow-up analysis, developed after the frozen evaluation, uses untreated source states to condition response transfer. Hyperparameters remain selected using source-only donor and cell-type holdouts. The selected module has MSE 0.011450 and 0.017577 in CD14 and CD16 monocytes, respectively. These are reductions of 4.01% and 2.86% relative to the frozen selected model. Its predictions are exactly identical to the Gaussian kernel ridge comparator in every fold. This supports the usefulness of cell-state information within this cohort. It does not establish an advantage beyond that classical comparator or constitute a second untouched validation.

Across the same 32 eligible Hallmark sets, mean-response MSE is 0.003694 and 0.003181, compared with 0.004056 and 0.003462 for the frozen model. Mean response Pearson correlation is 0.3959 and 0.3390. [Complete condition scores](benchmarks/parse_per_condition_metrics.tsv) and [analysis scope](benchmarks/parse_summary.json) accompany the results. Outer folds share source training donors.

### Cytokine specificity and donor consistency

An exact decomposition of fixed predictions separates error in the shared cytokine response from error in differences between cytokines. The cytokine-varying component accounts for 67.0% of the kernel model's MSE gain in CD14 monocytes and 56.7% in CD16 monocytes. MSE improves in eight and seven of twelve donors, respectively. Removing any single donor leaves the overall mean improvement positive in both populations. The paired interval for cytokine-centred MSE excludes zero in CD14 but includes zero in CD16. The donor with one eligible CD16 condition remains in the primary analysis. Its centred error is zero by definition, and its centred correlation is undefined.

[Decomposition by model](benchmarks/parse_specificity_model_decomposition.tsv), [donor results](benchmarks/parse_specificity_donor_decomposition.tsv), [condition-level changes](benchmarks/parse_specificity_condition_improvements.tsv) and [paired uncertainty and sensitivity](benchmarks/parse_specificity_summary.json) accompany this diagnostic. No prediction is refitted for the decomposition.

### Donor-reliability extension

A subsequent development analysis estimates which source cell-type differences recur across donors. It downweights response components with high donor variability and separately calibrates the shared response and the cell-state correction. Every inner donor and cell-type holdout re-estimates these quantities using only its training sources. A two-amplitude kernel without reliability weighting controls for the additional calibration. Cytokine-level and gene-level weighting are both evaluated, and all twelve source selections choose cytokine-level weighting.

| Predictor | CD14 MSE | CD16 MSE | CD14 response Pearson | CD16 response Pearson |
|---|---:|---:|---:|---:|
| Gaussian kernel ridge | 0.011450 | 0.017577 | 0.3959 | 0.3390 |
| Kernel with two amplitudes | 0.011469 | 0.017601 | 0.3938 | 0.3373 |
| Source-selected donor reliability | 0.011411 | 0.017533 | 0.4039 | 0.3467 |

The source-selected extension reduces MSE by 0.34% and 0.25% relative to Gaussian kernel ridge. The paired differences are −0.0000385 (95% interval −0.0001842 to 0.0001390) and −0.0000441 (−0.0002089 to 0.0001540). Both intervals include zero, as do those for response Pearson gains. The comparison retains the same 2,003 target pairs, source-control gene panels and donor weighting. These results describe follow-up development after the frozen evaluation, rather than an additional independent confirmation.

[All compared variants](benchmarks/parse_replicated_model_metrics.tsv), [donor scores](benchmarks/parse_replicated_donor_metrics.tsv), [condition scores](benchmarks/parse_replicated_per_condition_metrics.tsv), [paired intervals](benchmarks/parse_replicated_paired_intervals.tsv) and [source selections](benchmarks/parse_replicated_source_selections.tsv) provide the full comparison. Source-selected and cytokine-weighted predictions coincide and are not independent replications. This extension is an experimental analysis, not a replacement for the packaged trained transfer model.

The provider distributes the original Parse data under CC BY-NC 4.0. This repository includes analytical summaries, not raw cells. The code licence does not replace third-party data licences.

## Data verification

### Perturbation-specific information

Removing each gene's average response across drugs gives a correlation of 0.273 for the programme model, compared with 0.203 for the compound-only gate, 0.236 for the gene-only gate, 0.189 for fine-tuned scGPT and 0.190 for frozen Nicheformer. This diagnostic evaluates differences between drugs after removing a shared expression pattern. All predictions remain fixed.

The programme model lowers MSE for 110 of 127 drugs relative to compound-only weighting. Its paired mean difference is −0.002672, with a 95% compound-bootstrap interval of −0.003722 to −0.001700. The drug-varying component accounts for 84.0% of this improvement. Removing any single drug leaves the average difference negative. Randomly permuting complete predicted vectors across drug labels increases programme-model MSE from 0.073151 to 0.091463 on average. All drug-aware comparator families also outperform their shuffled predictions.

[Model diagnostics](benchmarks/specificity_model_metrics.tsv), [per-drug values](benchmarks/specificity_per_drug_metrics.tsv) and [paired comparisons](benchmarks/specificity_summary.json) include every compared model and all drugs. The three donor-stratified analyses retain shared source training donors and are distinct from the joint donor holdouts above.

### Technical repeatability

Ten disjoint-half partitions within each eligible treatment and control profile use 36,722 original myeloid cells across 421 profiles. Summing the two count halves exactly reconstructs every original profile. All 127 drugs are retained, with at least ten cells per half. Mean response correlation between halves is 0.354, or 0.360 after removing the shared response. These partitions measure cell-sampling repeatability within the same experiments. They are not independent biological replicates or a strict model-performance ceiling. [Partition scores](benchmarks/split_half_partition_metrics.tsv) and [drug-level repeatability](benchmarks/split_half_per_drug_repeatability.tsv) are provided.

### Distribution-metric sensitivity

The interferon comparison retains fixed predictions and source-only PCA transforms. Eighteen MMD settings combine 20 or 50 principal components, bandwidth multipliers of 0.5, 1 or 2, and requested sample sizes of 64, 128 or 256 cells per arm. Available cells cap each sample size equally across models. Five subsamples are averaged within each donor. Native-model distribution scores also average their three fits.

ContextDose has lower biased and unbiased squared MMD than scGen and scVIDR in both monocyte populations under all 18 settings, with every paired donor interval below zero. Energy distance gives the same direction across its six unique settings. This evidence concerns cell distributions. scVIDR retains lower CD16 mean-response MSE. Sensitivity settings are not independent replications.

[Setting means](benchmarks/distribution_sensitivity_setting_means.tsv), [donor scores](benchmarks/distribution_sensitivity_donor_results.tsv), [paired intervals](benchmarks/distribution_sensitivity_paired_intervals.tsv) and [summary](benchmarks/distribution_sensitivity_summary.json) accompany the analysis. Energy values repeat across bandwidths in the detailed tables, but the summary counts each of the six unique energy settings once.

### Original count reconstruction

Reaggregation of the released 298,087 single cells exactly reproduces all 1,813 published pseudobulk count profiles and their cell counts on the evaluation panel. The 21,265-gene original release stores raw counts in `AnnData.raw.X`; `AnnData.X` contains processed expression.

The task is a development evaluation on a public study. It does not establish clinical or unseen-compound performance. Primary data: [OP3 benchmark](https://doi.org/10.52202/079017-0650). Model sources: [scGPT](https://github.com/bowang-lab/scGPT) and [Nicheformer](https://github.com/theislab/nicheformer). Gene sets: [MSigDB Hallmarks](https://doi.org/10.1016/j.cels.2015.12.004).
