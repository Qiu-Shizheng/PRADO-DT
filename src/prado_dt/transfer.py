"""CPU inference for ContextDose compound/gene reliability transfer."""
import argparse,csv,json
from pathlib import Path
import numpy as np

def predict(control,gene_ids,compounds,doses_uM,times_hours,model_dir):
    directory=Path(model_dir);meta=json.loads((directory/'model.json').read_text())
    genes=list(map(str,gene_ids));expected=meta['gene_ids'];n=len(compounds)
    if not n or len(doses_uM)!=n or len(times_hours)!=n:raise ValueError('Supply equal, nonempty condition lists.')
    if len(set(genes))!=len(genes) or set(genes)!=set(expected):raise ValueError('Control gene identities must match the model exactly and be unique.')
    control=np.asarray(control,float)
    if control.shape not in [(len(genes),),(n,len(genes))] or not np.isfinite(control).all():raise ValueError('Provide one finite control vector, or one per condition.')
    order=[genes.index(g) for g in expected];control=control[...,order]
    lookup={(d['drug'].casefold(),float(d['dose_uM']),float(d['time_hours'])):i for i,d in enumerate(meta['conditions'])}
    indices=[]
    for drug,dose,time in zip(compounds,doses_uM,times_hours):
        key=(str(drug).casefold(),float(dose),float(time))
        if key not in lookup:raise ValueError('Unsupported drug, dose or time: '+str(key))
        indices.append(lookup[key])
    with np.load(directory/'model.npz',allow_pickle=False) as a:p=a['mean_effect'][indices];v=a['between_context_variance_of_mean'][indices]
    c=meta['selected_parameters'];t=c['reliability'];mix=c['gene_gate_mix'];signal=p*p
    if t==0:effect=c['scale']*p
    else:
        compound=signal.mean(1)/(signal.mean(1)+t*v.mean(1)+1e-12)
        gene=signal/(signal+t*v+1e-12)
        effect=c['scale']*((1-mix)*compound[:,None]+mix*gene)*p
    return control+effect,effect,np.asarray(expected)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model-dir',required=True)
    p.add_argument('--control',required=True);p.add_argument('--conditions',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.control) as f:ctl=list(csv.DictReader(f))
    with open(a.conditions) as f:cond=list(csv.DictReader(f))
    ids=[r['condition_id'] for r in cond]
    if len(set(ids))!=len(ids):raise ValueError('Condition IDs must be unique.')
    prediction,effect,genes=predict([float(r['expression']) for r in ctl],[r['gene_id'] for r in ctl],
        [r['drug'] for r in cond],[float(r['dose_uM']) for r in cond],[float(r['time_hours']) for r in cond],a.model_dir)
    np.savez_compressed(a.output,prediction=prediction,effect=effect,gene_ids=genes,condition_id=np.asarray(ids))
    print('Saved '+str(len(prediction))+' predicted conditions.')
if __name__=='__main__':main()
