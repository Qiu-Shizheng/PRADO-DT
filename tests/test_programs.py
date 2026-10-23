import unittest
from pathlib import Path
import numpy as np
from prado_dt.transfer import predict
from prado_dt.transfer_fit import fit_from_arrays

ROOT=Path(__file__).resolve().parents[1]

class ProgramTests(unittest.TestCase):
    def test_replays_independent_study_predictions(self):
        with np.load(ROOT/'tests/program_reference.npz') as z:
            args=[z[k] for k in ['control','gene_ids','compounds','doses_uM','times_hours']]
            actual=predict(*args,ROOT/'models/response_transfer/op3_programs')[0]
            np.testing.assert_allclose(actual,z['prediction'],rtol=0,atol=1e-12)
            order=np.arange(len(z['gene_ids']))[::-1]
            actual_reordered=predict(z['control'][:,order],z['gene_ids'][order],*args[2:],ROOT/'models/response_transfer/op3_programs')[0]
            np.testing.assert_array_equal(actual_reordered,actual)

    def test_program_search_preserves_gene_only_option(self):
        e=np.random.default_rng(91).normal(size=(4,8,15))+.4
        fitted=fit_from_arrays(e,search='programs')
        self.assertLessEqual(fitted['source_validation_relative_mse'],
            fitted['source_selection']['gene_families']['gene']['source_relative_mse']+1e-12)

    def test_zero_response_does_not_produce_invalid_selection(self):
        with self.assertRaises(ValueError):fit_from_arrays(np.zeros((4,5,10)),search='programs')

    def test_single_gene_panel_retains_a_valid_basis(self):
        fitted=fit_from_arrays(np.array([[[1.],[2.]],[[1.1],[1.8]],[[.9],[2.1]]]),search='programs')
        self.assertEqual(fitted['program_basis'].shape,(1,1))
        self.assertTrue(np.isfinite(fitted['source_validation_relative_mse']))

if __name__=='__main__':unittest.main()
