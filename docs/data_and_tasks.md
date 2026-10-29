# Data and prediction tasks

scPerturbMix studies a practical question: can responses measured in some cell types, donors or treatment conditions help predict a response that has not yet been measured? Its output is a gene-expression change for a cell population. The evaluated interventions include drugs, immune signals and gene repression.

The evaluation contains **11 experiments from 10 original studies**. Ten experiments are derived from single-cell RNA measurements. The diffuse midline glioma screen uses bulk RNA measurements from whole wells. The two sci-Plex experiments share one original publication. Multiple prediction tasks, cell populations or pilot budgets from the same study do not create additional independent datasets.

The [cohort table](data/cohort_roles_20261028.tsv) provides an English, machine-readable record of all 11 experiments, their source publications, data transformations and training roles.

## What the model learns

The released response-transfer model is a statistical machine-learning model. It estimates average perturbation responses, measures their variation across source contexts and selects reliability weights using held-out source data. Its programme extension learns low-dimensional directions in source response variation. Biological pathway annotations, such as Hallmark sets, are used for interpretation and evaluation after prediction.

For the released response-transfer checkpoints, the untreated target profile is added to the predicted response at the final step. It sets the expression baseline. The predicted response itself is determined by the source data and the fitted treatment model. The target-context kernel extension additionally uses similarity between untreated cell states to estimate a target-specific response. The benchmark evaluates this extension separately from the exported core response checkpoints.

The software also includes an optional neural reference implementation. The main fitted response checkpoints use NumPy inference and do not require a GPU. See the [response-transfer guide](response_transfer.md) for the training array and model-file format.

## Five prediction tasks

| Task | Biological question | Data |
|---|---|---|
| Drug responses across cell contexts | Can responses in one group of cells predict how another cell population responds to a known drug? | OP3 immune-cell drug screen, Cellarity cultured-to-primary screen |
| Immune responses across donors and cell types | Can immune responses from other donors and cell types predict the response of a new donor's monocytes? | Kang interferon-beta, Parse cytokines, Wood stimulation |
| Dose response | Can measured doses predict responses at an unmeasured concentration? | sci-Plex2, sci-Plex3 |
| Genetic perturbations across environments | How does the effect of reducing a gene's activity transfer across a cell background, drug environment or donor? | Glioblastoma kinome screen, PerturbFate, primary CD4 T-cell panel |
| Prediction after a small pilot experiment | How much do a few measured target responses help predict the remaining stimuli? | Parse and Wood, reusing their donors and experiments |

The first four rows describe biological tasks. The fifth changes the amount of target information available. The bulk glioma screen is an auxiliary drug-transfer evaluation.

## Training, validation and testing

Training data determine fitted parameters. Validation data select settings such as response weights and programme rank. Test data measure prediction performance after that selection. A **source context** is a cell type, donor or experimental background whose treated response is available for training. A **target context** is the population whose treated response is being predicted.

Untreated target cells are usually available. In a zero-support task, no treated target response is supplied. In a pilot task, a defined set of treated target responses is supplied and the remaining query responses are kept separate. These information budgets are compared separately.

| Dataset | Training | Validation | Test |
|---|---|---|---|
| OP3 immune-cell drug screen | B, T and natural killer cells | Held-out source populations. Joint donor tasks also withhold source donors. | Myeloid responses. Pooled cell-type transfer shares donors. Joint donor–cell-type transfer additionally withholds the target donor. |
| Cellarity cultured-to-primary screen | Six cultured cell backgrounds | Leave one source background out | Four primary-cell populations: blood progenitors, CD8 T cells, bronchial epithelial cells and preadipocytes |
| Kang interferon-beta | Lymphoid cells from seven donors per fold | Source-only donor and cell-type validation, or a rule fixed in OP3 | Two monocyte populations from the eighth donor, repeated across eight donors |
| Parse cytokines | Seven lymphoid populations from eleven donors per fold | Joint source donor and cell-type holdouts | CD14 and CD16 monocytes from the held-out donor, across twelve donor folds |
| Wood stimulation | Five lymphoid populations from the other five donors in the same batch | Joint source donor and cell-type holdouts using the parameter grid fixed in Parse | Held-out donor monocytes, with batch-specific stimulus panels and pilot budgets |
| sci-Plex3 | Lowest and highest doses in three cell lines | A fixed fraction of endpoint-dose source cells | Two intermediate doses in the same three cell lines, giving 54 conditions |
| sci-Plex2 | Eligible samples at 0.1, 1, 10 and 100 µM | Samples at 0.5 µM | Seven eligible conditions at 5 or 50 µM |
| Glioblastoma kinome screen | A172 glioblastoma conditions | T98G for selection. Separate A172 conditions for interval calibration. | U87MG development evaluation |
| PerturbFate | 80 target genes | 26 target genes | Drug-treated responses of 27 held-out genes, with their vehicle responses available as inputs |
| Primary CD4 T-cell panel | Two donors, each with resting and two activated states | A third donor | A fourth donor in the same three states |
| Diffuse midline glioma PLATE-seq | First DIPG6 plate | Second DIPG6 plate | Two SF8628 plates |

## What each dataset represents

**OP3: drug responses in human blood immune cells.** The screen includes three donors and 127 drugs. B cells, T cells and natural killer cells provide source responses. Myeloid cells are the target population. The released analysis uses 5,317 response genes and matched donor, cell-type and experimental-library controls. The original raw data contain 298,087 cells. Prediction endpoints are aggregated response profiles. [Original study](https://doi.org/10.52202/079017-0650).

**Cellarity: cultured cells to primary human cells.** The release contains 1,737 aggregated profiles across ten cell backgrounds. Six cultured backgrounds supply source responses. Targets are CD34-positive blood progenitors, CD8-positive T cells, bronchial epithelial cells and preadipocytes. The shared evaluation includes 44 conditions for three populations and four conditions for CD8 T cells. These populations represent different tissues and functions, rather than four interchangeable technical replicates. [Original study](https://doi.org/10.1126/science.adi8577).

**Kang: interferon responses across donors.** Interferon-beta is an immune signal. This experiment measured stimulated and untreated blood immune cells from eight people with lupus. The analysis retains 23,981 annotated singlets and predicts CD14-positive and FCGR3A-positive monocyte responses. CD14 and FCGR3A distinguish two monocyte populations. Treatment and control used different sequencing lanes, so lane effects accompany the original experimental contrast. [Original study](https://doi.org/10.1038/nbt.4042).

**Parse: a large cytokine-response atlas.** Cytokines are signals that regulate immune activity. The public resource contains 9,697,974 cells from twelve healthy donors exposed to 90 cytokines or a control for 24 hours. The principal evaluation contains 2,003 eligible monocyte responses. Each donor occupies one experimental plate. Pilot analyses reuse this resource to predict unmeasured stimuli after observing 4, 8 or 16 target-context responses. This is an official public data release. [Dataset and experimental design](https://www.parsebiosciences.com/datasets/10-million-human-pbmcs-in-a-single-experiment/).

**Wood: independent immune-stimulation experiments.** This study contains 153,443 cells from twelve healthy donors exposed to eleven immune stimuli for 48 hours. Two batches contain six different donors each and use different stimulus panels. Complete pilot analyses include five donors in batch A and six in batch B under the minimum-cell rule. The target population is the authors' broad monocyte annotation. The study provides an independent experimental setting for the protocol established in Parse. [Original study](https://doi.org/10.1186/s13073-026-01721-y).

**sci-Plex3: drug dose in three cancer cell lines.** The evaluated subset contains 26,046 cells from A549 lung cancer, K562 leukaemia and MCF7 breast cancer cells treated with nine drugs. Training uses 10 and 10,000 nM. Testing uses 100 and 1,000 nM. The model comparison uses a fixed 512-gene panel from the released processed matrix. [Original study](https://doi.org/10.1126/science.aax6234).

**sci-Plex2: four drugs across multiple doses.** This experiment measures A549 lung cancer cells treated with BMS-345541, dexamethasone, nutlin-3A or vorinostat. Cells are aggregated by experimental hash label. Six of the seven evaluation conditions lie between eligible training doses. Nutlin-3A at 50 µM is an extrapolation condition because its 100 µM source samples fail the cell-coverage threshold. Hash labels are experimental indices, not independent donors. [Original study](https://doi.org/10.1126/science.aax6234).

**Glioblastoma kinome screen: gene repression with drug treatment.** CRISPR interference reduces a gene's activity. This experiment combines gene repression with drug exposure in A172, T98G and U87MG glioblastoma cell lines. The analysed cohort contains 196,731 cells with validated guide identities. U87MG has been used during model development. Many treatment conditions contain few cells, and measured drug-specific effects show limited split-half repeatability. This experiment therefore supplies development evidence and a measurement-sensitivity analysis. [Original study](https://doi.org/10.1016/j.xgen.2023.100487).

**PerturbFate: genetic changes under an anticancer drug.** This experiment represses genes in A375 melanoma cells with or without vemurafenib, a BRAF inhibitor. Genes are divided into training, validation and evaluation groups. The prediction task supplies the vehicle response of an evaluation gene and predicts its response under drug treatment. This is conditional genetic-effect prediction in a known cell line. [Original study](https://doi.org/10.1038/s41586-026-10367-0).

**Primary CD4 T cells: immune regulators across donors.** CD4 T cells help coordinate immune activity. The evaluated panel contains sixteen prespecified regulators in resting cells and cells activated for 8 or 48 hours. Fifteen regulators meet the cell-coverage requirement. Twelve shared targets contribute 35 test conditions. This focused panel tests donor generalisation within known activation states. [Original study](https://doi.org/10.1016/j.cell.2026.08.002).

**Diffuse midline glioma: auxiliary bulk drug screening.** This brain-tumour screen measures whole-well RNA after 372 drug treatments. It includes two plates each from DIPG6 and SF8628 cells. It uses bulk PLATE-seq, so its evidence is listed separately from the single-cell experiments. Doses differ between cell lines for 114 drugs. The evaluated expression endpoint has limited replicate drug-response agreement and differs from the original study's regulatory-protein activity endpoint. [Original study](https://doi.org/10.1038/s41588-026-02550-w).

## Interpreting external validation

| Evaluation setting | What stays fixed | What is fitted in the new study |
|---|---|---|
| Independent-study evaluation with source fitting | Task definition, permitted inputs and selection procedure | Parameters estimated from allowed source cells in that study |
| Fixed-rule transfer | An existing rule or candidate parameter grid | Source response coefficients or other permitted fitted weights |
| Entirely frozen-model transfer | All fitted model weights and preprocessing rules | Nothing |

The OP3-to-Kang and Parse-to-Wood analyses transfer fixed rules while fitting permitted source information in the new study. The eleven-experiment evaluation covers several study-specific fitted models. It should be read according to the setting recorded for each task. Development targets that have already informed architecture work are identified in the cohort table.

Immune-stimulation datasets measure changes caused by immune signals. They do not contain clinical checkpoint-inhibitor response, patient survival or other treatment-outcome labels. Those outcomes would require independently labelled patient cohorts and a corresponding prediction endpoint.

## Expression scales and quality

The expression target is defined separately for each dataset. Kang, Parse and Wood use per-cell log1p counts per 10,000, calculated from complete measured libraries, followed by a condition mean. Several other datasets use log1p counts per million after summing cells within experimental profiles. Cellarity and sci-Plex3 retain their published processed scales. OP3 uses its released 5,317-gene denominator. These transformations produce different numerical endpoints, so MSE values from different datasets should not be compared directly.

Comparisons within a task use the same target conditions, gene set, normalisation, controls and available target information. Feature provenance is also recorded. The sci-Plex3 panel comes from the published processed feature set. The glioblastoma panel excludes U87MG during feature selection but can include the T98G validation background. Source-selected panels are identified separately in the cohort table.

Data checks cover identities, finite nonnegative counts, library totals, cell coverage and matched controls. Cellarity requires cell background, library and well together to identify a profile because its released integer row labels repeat. Molecular count data and estimated bulk counts have different integer requirements. Eligibility thresholds are applied independently of model accuracy. Low response repeatability is reported as a property of the measured endpoint.

## Choosing data for a new application

Use source experiments with matched treatment controls, compatible gene identities and a common expression transformation. Keep the intended target context separate before selecting parameters. For donor generalisation, split by donor. For new genes, keep all guides for a gene in the same partition. Pilot designs should fix the support and query conditions before inspecting query responses.

The packaged training interface expects at least three source contexts with the same ordered treatment conditions and genes. Existing drug checkpoints accept their listed drug–dose–time combinations. For another experimental scale or treatment panel, fit a compatible model from source effects using the [training instructions](../README.md#fit-your-own-response-model).
