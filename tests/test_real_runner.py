"""Evaluation orchestration contracts, not model accuracy claims."""
import json
from pathlib import Path
import tempfile
import unittest
from src.real_evaluation import resolve_systems,run_inference


class RealRunnerTests(unittest.TestCase):
    def setUp(self):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir='.cache/tests');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_parent_must_precede_derived_system(self):
        path=self.root/'systems.json'
        path.write_text(json.dumps({'systems':[{'id':'derived','refine_from':'absent'}]}))
        with self.assertRaisesRegex(ValueError,'earlier parent'):
            resolve_systems(path)

    def test_missing_model_executable_has_exact_blocker_and_no_substitution(self):
        audio=self.root/'audio.wav';audio.write_bytes(b'fixture')
        result=run_inference({'id':'unavailable','python':str(self.root/'missing.exe')},audio,self.root,{})
        self.assertEqual(result['status'],'unavailable')
        self.assertIn('error',result);self.assertNotIn('report_path',result)

    def test_derived_system_never_substitutes_parent_from_previous_run(self):
        audio=self.root/'audio.wav';audio.write_bytes(b'fixture')
        result=run_inference({'id':'derived','refine_from':'parent'},audio,self.root,{})
        self.assertEqual(result['status'],'unavailable')
        self.assertIn('exact comparison',result['error'])


if __name__=='__main__':
    unittest.main()
