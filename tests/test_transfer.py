import unittest
from pathlib import Path
import numpy as np
from prado_dt.transfer import predict
from prado_dt.transfer_fit import fit_from_arrays,effect_prediction

ROOT=Path(__file__).resolve().parents[1]

class TransferTests(unittest.TestCase):
    def setUp(self):
        with np.load(ROOT/'tests/transfer_reference.npz',allow_pickle=False) as z:self.reference={k:z[k] for k in z.files}
        self.model=ROOT/'models/response_transfer/op3'

    def run_model(self,control=None,genes=None,compounds=None):
        r=self.reference
        return predict(r['control'] if control is None else control,r['gene_ids'] if genes is None else genes,
          r['compounds'] if compounds is None else compounds,r['doses_uM'],r['times_hours'],self.model)[0]

    def test_replays_fixed_study_predictions(self):
        np.testing.assert_allclose(self.run_model(),self.reference['prediction'],rtol=0,atol=1e-12)

    def test_gene_order_does_not_change_prediction(self):
        r=self.reference;order=np.arange(len(r['gene_ids']))[::-1]
        np.testing.assert_array_equal(self.run_model(),self.run_model(r['control'][:,order],r['gene_ids'][order]))

    def test_rejects_unknown_compound_and_missing_gene(self):
        with self.assertRaises(ValueError):self.run_model(compounds=['not_in_model']*3)
        with self.assertRaises(ValueError):self.run_model(self.reference['control'][:,:-1],self.reference['gene_ids'][:-1])

    def test_shared_source_response_is_preserved(self):
        e=np.broadcast_to(np.array([[1.,-2.,3.],[2.,1.,-1.]]),(4,2,3)).copy()
        fitted=fit_from_arrays(e)
        self.assertEqual(fitted['source_validation_relative_mse'],0.)
        self.assertEqual(fitted['selected_parameters'],{'reliability':0.,'gene_gate_mix':0.,'scale':1.})

    def test_context_order_does_not_change_selection(self):
        e=np.random.default_rng(3).normal(size=(5,4,7))+1
        a=fit_from_arrays(e);b=fit_from_arrays(e[::-1])
        self.assertEqual(a['selected_parameters'],b['selected_parameters'])
        np.testing.assert_allclose(a['mean_effect'],b['mean_effect'],rtol=0,atol=1e-14)

    def test_source_design_is_required(self):
        for e in [np.ones((2,3,4)),np.zeros((3,3,4)),np.full((3,3,4),np.nan)]:
            with self.assertRaises(ValueError):fit_from_arrays(e)

    def test_extended_scale_minimizes_direct_source_risk(self):
        e=np.random.default_rng(21).normal(size=(4,6,9))+.5
        fitted=fit_from_arrays(e,search='extended');cfg=fitted['selected_parameters']
        def risk(scale):
            values=[]
            for held in range(len(e)):
                source=np.delete(e,held,0)
                pr=effect_prediction(source.mean(0),source.var(0,ddof=1)/len(source),{**cfg,'scale':scale})
                values.append(np.mean((pr-e[held])**2)/np.mean(e[held]**2))
            return np.mean(values)
        self.assertAlmostEqual(risk(cfg['scale']),fitted['source_validation_relative_mse'],places=12)
        for scale in np.linspace(0,2,201):self.assertLessEqual(risk(cfg['scale']),risk(scale)+1e-12)
        for bad in ['unknown',None]:
            with self.assertRaises(ValueError):fit_from_arrays(e,search=bad)

if __name__=='__main__':unittest.main()
