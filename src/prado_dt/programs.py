"""Source-only response shrinkage in gene and learned program coordinates."""
import itertools
import numpy as np
from scipy.linalg import eigh

PENALTIES=np.r_[0.,np.logspace(-3,3,49)]
MIXES=np.linspace(0,1,9)
PROGRAM_PENALTIES=[0.,.01,.1,.3,1.,3.,10.,30.,100.]
RANKS=[4,8,16,32,64]
BLENDS=[0.,.25,.5,.75,1.]

def moments(effects):
    return effects.mean(0),effects.var(0,ddof=1)/len(effects)

def shrink(mean,variance,penalty,mix):
    if penalty==0:return mean.copy()
    squared=mean*mean
    global_gate=squared.mean(1)/(squared.mean(1)+penalty*variance.mean(1)+1e-12)
    gene_gate=squared/(squared+penalty*variance+1e-12)
    return ((1-mix)*global_gate[:,None]+mix*gene_gate)*mean

def calibrated(a,b):
    scale=float(np.clip(b/max(a,1e-20),0,2))
    return scale,float(1-2*scale*b+scale*scale*a)

def select_gene(effects,validation=None):
    folds=[]
    validation=validation if validation is not None else [(np.delete(effects,held,0),effects[held]) for held in range(len(effects))]
    for source,truth in validation:
        mean,var=moments(source)
        if np.mean(truth*truth)<=1e-12:raise ValueError('Source validation response has zero energy')
        folds.append((mean,var,truth,float(np.mean(truth*truth))))
    candidates=[]
    for penalty in PENALTIES:
        aa=np.zeros(len(MIXES));bb=aa.copy()
        for mean,var,truth,den in folds:
            q=shrink(mean,var,penalty,0);difference=shrink(mean,var,penalty,1)-q
            aa+=(np.mean(q*q)+2*MIXES*np.mean(q*difference)+MIXES**2*np.mean(difference*difference))/den/len(folds)
            bb+=(np.mean(q*truth)+MIXES*np.mean(difference*truth))/den/len(folds)
        for i,mix in enumerate(MIXES):
            if penalty==0 and mix!=0:continue
            scale,risk=calibrated(aa[i],bb[i])
            candidates.append(dict(reliability=float(penalty),gene_gate_mix=float(mix),scale=scale,source_relative_mse=risk))
    families={'global':lambda c:c['reliability']==0,'compound':lambda c:c['gene_gate_mix']==0,'gene':lambda c:True}
    return {k:min((c for c in candidates if include(c)),key=lambda c:c['source_relative_mse']) for k,include in families.items()},candidates

def basis(effects,rank):
    matrix=effects.reshape(-1,effects.shape[-1])
    rank=max(1,min(rank,min(matrix.shape)-1))
    eigenvalues,vectors=eigh(matrix@matrix.T,subset_by_index=[matrix.shape[0]-rank,matrix.shape[0]-1])
    order=np.argsort(eigenvalues)[::-1];eigenvalues=eigenvalues[order];vectors=vectors[:,order]
    keep=eigenvalues>max(eigenvalues[0]*1e-12,1e-20)
    result=matrix.T@vectors[:,keep]/np.sqrt(eigenvalues[keep])[None,:]
    assert np.max(np.abs(result.T@result-np.eye(result.shape[1])))<1e-7
    return result

def fit(effects,validation=None):
    """Select every module on leave-one-source-context-out response error."""
    effects=np.asarray(effects,float)
    assert effects.ndim==3 and len(effects)>=3 and np.isfinite(effects).all()
    validation=validation if validation is not None else [(np.delete(effects,held,0),effects[held]) for held in range(len(effects))]
    for source,truth in validation:
        assert len(source)>=2 and source.shape[1:]==truth.shape==effects.shape[1:]
        assert np.isfinite(source).all() and np.isfinite(truth).all()
    selected,grid=select_gene(effects,validation);cfg=selected['gene'];folds=[]
    for source,truth in validation:
        mean,var=moments(source)
        gene=shrink(mean,var,cfg['reliability'],cfg['gene_gate_mix'])
        u=basis(source,max(RANKS));coordinates=source@u
        folds.append((u,*moments(coordinates),gene,truth,float(np.mean(truth*truth))))
    candidates=[]
    for rank,penalty,program_mix in itertools.product(RANKS,PROGRAM_PENALTIES,[0.,.5,1.]):
        if penalty==0 and program_mix!=0:continue
        aa=np.zeros(len(BLENDS));bb=aa.copy();alpha=np.array(BLENDS)
        for u,mean,var,gene,truth,den in folds:
            v=u[:,:rank];latent=shrink(mean[:,:rank],var[:,:rank],penalty,program_mix)
            # Orthonormality gives the squared error without repeatedly
            # reconstructing the full gene matrix for every blend.
            a_gene=np.mean(gene*gene);a_program=np.sum(latent*latent)/gene.size
            cross=np.sum((gene@v)*latent)/gene.size
            b_gene=np.mean(gene*truth);b_program=np.sum((truth@v)*latent)/gene.size
            aa+=((1-alpha)**2*a_gene+alpha**2*a_program+2*alpha*(1-alpha)*cross)/den/len(folds)
            bb+=((1-alpha)*b_gene+alpha*b_program)/den/len(folds)
        for j,blend in enumerate(BLENDS):
            if blend==0 and (rank!=RANKS[0] or penalty!=0):continue
            scale,risk=calibrated(aa[j],bb[j])
            candidates.append(dict(rank=rank,program_reliability=penalty,program_gate_mix=program_mix,program_blend=blend,scale=scale,source_relative_mse=risk))
    best=min(candidates,key=lambda c:c['source_relative_mse'])
    lowrank=min((c for c in candidates if c['program_blend']==1 and c['program_reliability']==0),key=lambda c:c['source_relative_mse'])
    u=basis(effects,max(RANKS))
    return {'gene_families':selected,'program_model':best,'lowrank_baseline':lowrank,'gene_grid':grid,'program_grid':candidates},u

def predict(effects,selection,u):
    mean,var=moments(effects);predictions={}
    for name,cfg in selection['gene_families'].items():
        predictions[name]=cfg['scale']*shrink(mean,var,cfg['reliability'],cfg['gene_gate_mix'])
    gc=selection['gene_families']['gene'];gene=shrink(mean,var,gc['reliability'],gc['gene_gate_mix'])
    for name,cfg in [('lowrank',selection['lowrank_baseline']),('program_gene',selection['program_model'])]:
        v=u[:,:cfg['rank']];m,w=moments(effects@v)
        program=shrink(m,w,cfg['program_reliability'],cfg['program_gate_mix'])@v.T
        predictions[name]=cfg['scale']*((1-cfg['program_blend'])*gene+cfg['program_blend']*program)
    return predictions
