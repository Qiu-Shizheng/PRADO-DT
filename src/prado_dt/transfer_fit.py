"""Fit hierarchical response-reliability models using source contexts only."""
import argparse,itertools,json
from pathlib import Path
import numpy as np

def effect_prediction(mean,variance,config):
    penalty=config['reliability'];mix=config['gene_gate_mix'];square=mean*mean
    if penalty==0:return config['scale']*mean
    compound=square.mean(1)/(square.mean(1)+penalty*variance.mean(1)+1e-12)
    gene=square/(square+penalty*variance+1e-12)
    return config['scale']*((1-mix)*compound[:,None]+mix*gene)*mean

def _extended_candidates(e):
    """Fit scale analytically for each reliability penalty and gate mixture."""
    mixes=np.linspace(0,1,9);configs=[];scores=[]
    for penalty in np.r_[0.,np.logspace(-3,3,49)]:
        quadratic=np.zeros(len(mixes));linear=np.zeros(len(mixes))
        for held in range(len(e)):
            source=np.delete(e,held,axis=0);mean=source.mean(0);variance=source.var(0,ddof=1)/len(source)
            square=mean*mean;den=float(np.mean(e[held]**2))
            if den<=1e-12:raise ValueError('A source validation context has no measurable response for normalised selection.')
            compound=np.ones(mean.shape[0]) if penalty==0 else square.mean(1)/(square.mean(1)+penalty*variance.mean(1)+1e-12)
            gene=np.ones_like(mean) if penalty==0 else square/(square+penalty*variance+1e-12)
            base=compound[:,None]*mean;delta=gene*mean-base
            quadratic+=(np.mean(base*base)+2*mixes*np.mean(base*delta)+mixes**2*np.mean(delta*delta))/(den*len(e))
            linear+=(np.mean(base*e[held])+mixes*np.mean(delta*e[held]))/(den*len(e))
        scales=np.clip(linear/np.maximum(quadratic,1e-20),0,2)
        values=1-2*scales*linear+scales**2*quadratic
        for i,mix in enumerate(mixes):
            if penalty==0 and mix!=0:continue
            configs.append({'reliability':float(penalty),'gene_gate_mix':float(mix),'scale':float(scales[i])})
            scores.append(float(values[i]))
    return configs,np.asarray(scores)

def fit_from_arrays(effects,search='standard'):
    """Select a gate by leave-one-source-context-out, no-effect-normalised MSE.

    effects has shape (source contexts, shared conditions, response genes).
    Each vector is relative to the matched untreated source control.
    All source contexts must contain the same ordered conditions and genes.
    search='extended' uses a wider penalty range and source-fitted continuous
    scaling. The default preserves the original 65-configuration search.
    search='programs' also selects a source-learned programme basis and the
    mixture of gene-coordinate and programme-coordinate reliability.
    """
    e=np.asarray(effects,float)
    if e.ndim!=3 or e.shape[0]<3 or min(e.shape[1:])<1 or not np.isfinite(e).all():
        raise ValueError('Supply a finite context-by-condition-by-gene array with at least three source contexts.')
    if search not in ['standard','extended','programs']:raise ValueError('search must be standard, extended or programs')
    if search=='programs':
        from .programs import fit,moments
        selection,basis=fit(e)
        mean,variance=moments(e);latent_mean,latent_variance=moments(e@basis)
        return {'mean_effect':mean,'between_context_variance_of_mean':variance,
                'program_basis':basis,'program_mean':latent_mean,'program_variance':latent_variance,
                'selected_parameters':selection['gene_families']['gene'],
                'program_parameters':selection['program_model'],
                'source_validation_relative_mse':selection['program_model']['source_relative_mse'],
                'source_selection':selection}
    configs=[{'reliability':t,'gene_gate_mix':g,'scale':s}
             for t,g,s in itertools.product([0.,.25,1.,4.],[0.,.25,.5,1.],[0.,.5,.75,1.,1.25])
             if not(t==0 and g!=0)]
    scores=[]
    for held in range(len(e)):
        source=np.delete(e,held,axis=0);mean=source.mean(0);variance=source.var(0,ddof=1)/len(source)
        null=float(np.mean(e[held]**2))
        if null<=1e-12:raise ValueError('A source validation context has no measurable response for normalised selection.')
        scores.append([float(np.mean((effect_prediction(mean,variance,c)-e[held])**2))/null for c in configs])
    values=np.mean(scores,axis=0)
    if search=='extended':configs,values=_extended_candidates(e)
    selected=int(np.argmin(values))
    return {'mean_effect':e.mean(0),'between_context_variance_of_mean':e.var(0,ddof=1)/len(e),
            'selected_parameters':configs[selected],'source_validation_relative_mse':float(values[selected]),
            'candidate_scores':[{'parameters':c,'relative_mse':float(v)} for c,v in zip(configs,values)]}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-effects',required=True)
    p.add_argument('--output',required=True);p.add_argument('--input-scale',required=True)
    p.add_argument('--search',choices=['standard','extended','programs'],default='standard')
    a=p.parse_args();out=Path(a.output)
    if out.exists() and any(out.iterdir()):raise ValueError('Choose an empty output directory to preserve existing models.')
    with np.load(a.source_effects,allow_pickle=False) as z:
        effects=z['effects'];genes=z['gene_ids'].astype(str).tolist();drugs=z['drug'].astype(str)
        doses=np.asarray(z['dose_uM'],float);times=np.asarray(z['time_hours'],float)
    if effects.ndim!=3 or len(genes)!=effects.shape[2] or len(set(genes))!=len(genes):raise ValueError('Gene identity axis is invalid.')
    if any(len(v)!=effects.shape[1] for v in [drugs,doses,times]) or not(np.isfinite(doses).all() and np.isfinite(times).all()):raise ValueError('Condition metadata are invalid.')
    if np.any(doses<0) or np.any(times<0):raise ValueError('Dose and time must be nonnegative.')
    keys=list(zip(np.char.lower(drugs).tolist(),doses.tolist(),times.tolist()))
    if len(set(keys))!=len(keys):raise ValueError('Drug, dose and time combinations must be unique.')
    fitted=fit_from_arrays(effects,search=a.search);out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(out/'model.npz',**{k:v for k,v in fitted.items() if isinstance(v,np.ndarray)})
    metadata={'name':'ContextDose hierarchical response transfer','gene_ids':genes,
      'conditions':[{'drug':str(d),'dose_uM':float(c),'time_hours':float(t)} for d,c,t in zip(drugs,doses,times)],
      'source_context_count':len(effects),'input_scale':a.input_scale,'selected_parameters':fitted['selected_parameters'],'source_search':a.search}
    if 'program_parameters' in fitted:metadata['program_parameters']=fitted['program_parameters']
    (out/'model.json').write_text(json.dumps(metadata,indent=2))
    (out/'source_validation.json').write_text(json.dumps({k:v for k,v in fitted.items() if not isinstance(v,np.ndarray)},indent=2))
    print('Saved source-selected model to '+str(out))

if __name__=='__main__':main()
