"""Inference for the frozen ContextDose glioblastoma expression model."""
import argparse,csv,json
from pathlib import Path
import numpy as np

def predict(control, gene_ids, compounds, dose_levels, model_dir=None):
    model_dir=Path(model_dir or Path(__file__).resolve().parent)
    meta=json.loads((model_dir/'model.json').read_text())
    ids=list(map(str,gene_ids));expected=meta['expression_gene_ids']
    if len(ids)!=len(set(ids)):raise ValueError('Control gene identifiers must be unique.')
    if set(ids)!=set(expected):raise ValueError('Control must contain exactly the 512 model genes.')
    control=np.asarray(control,dtype=float)
    if control.shape!=(len(ids),) or not np.isfinite(control).all():raise ValueError('Supply one finite expression value per gene.')
    if len(compounds)!=len(dose_levels):raise ValueError('Compounds and dose levels must have equal length.')
    control=control[[ids.index(g) for g in expected]]
    with np.load(model_dir/'model.npz',allow_pickle=False) as saved:
        mean=saved['source_mean'];offsets=saved['drug_offsets']
    lookup={(str(drug),float(dose)):i for i,(drug,dose) in enumerate(meta['drug_doses'])}
    indexes=[]
    for drug,dose in zip(compounds,dose_levels):
        key=(str(drug).lower(),float(dose))
        if key not in lookup:raise ValueError('Unsupported compound/dose level: '+str(key))
        indexes.append(lookup[key])
    prediction=mean+meta['control_weight']*(control-mean)+meta['drug_weight']*offsets[indexes]
    return prediction,np.asarray(expected)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--control',required=True,help='CSV with gene_id,expression columns')
    p.add_argument('--conditions',required=True,help='CSV with condition_id,drug,dose_level columns')
    p.add_argument('--output',required=True,help='Output .npz archive')
    a=p.parse_args()
    with open(a.control) as f:control=list(csv.DictReader(f))
    with open(a.conditions) as f:conditions=list(csv.DictReader(f))
    ids=[r['condition_id'] for r in conditions]
    if not conditions or len(ids)!=len(set(ids)):raise ValueError('Conditions must be nonempty and have unique IDs.')
    prediction,genes=predict([float(r['expression']) for r in control],[r['gene_id'] for r in control],
      [r['drug'] for r in conditions],[float(r['dose_level']) for r in conditions])
    np.savez_compressed(a.output,prediction=prediction,expression_gene_ids=genes,condition_id=np.asarray(ids))
    print(f'Saved {prediction.shape[0]} conditions by {prediction.shape[1]} genes to {a.output}')
if __name__=='__main__':main()
