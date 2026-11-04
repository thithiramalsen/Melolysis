"""Adapter contract tests use stubs, not evidence of pretrained inference accuracy."""
from pathlib import Path
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch
from src.schema import AnalysisConfig
from src.note_models import import_midi, transcribe_basic_pitch, transcribe_external, model_identity
from src.pitch import EstimatorUnavailable
from tests.test_transcription import track


class ModelContractTests(unittest.TestCase):
    def setUp(self):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir='.cache/tests');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_midi_seconds_offset_and_unknown_confidence(self):
        import pretty_midi
        midi=pretty_midi.PrettyMIDI(initial_tempo=90)
        inst=pretty_midi.Instrument(0)
        inst.notes=[pretty_midi.Note(80,64,.5,1.2)]
        midi.instruments.append(inst);midi.write(str(self.root/'prediction.mid'))
        ns=import_midi(self.root/'prediction.mid', 'game',.1)
        self.assertAlmostEqual(ns[0].start,.6,delta=.002)
        self.assertEqual(ns[0].confidence,0)
        self.assertIn('confidence_unavailable',ns[0].flags)

    def test_polyphonic_import_requires_review(self):
        import pretty_midi
        midi=pretty_midi.PrettyMIDI();inst=pretty_midi.Instrument(0)
        inst.notes=[pretty_midi.Note(80,64,0,1),pretty_midi.Note(80,67,.5,1.5)]
        midi.instruments.append(inst);midi.write(str(self.root/'poly.mid'))
        with self.assertRaisesRegex(ValueError,'overlap'):
            import_midi(self.root/'poly.mid')

    def test_basic_pitch_amplitude_is_not_confidence(self):
        import numpy as np
        import soundfile as sf
        sf.write(self.root/'source.wav',np.ones(22050)*.1,22050)
        package=ModuleType('basic_pitch');package.ICASSP_2022_MODEL_PATH='stub-model'
        inference=ModuleType('basic_pitch.inference')
        def predict(*args,**kwargs):
            self.assertEqual(kwargs['minimum_frequency'],AnalysisConfig().fmin)
            return {},None,[(.1,.5,64,.99,None)]
        inference.predict=predict
        with patch.dict('sys.modules',{'basic_pitch':package,'basic_pitch.inference':inference}),patch('src.note_models.basic_pitch_model',return_value=object()):
            ns=transcribe_basic_pitch(self.root/'source.wav',track([64]*100),work_root=self.root/'work')
        self.assertEqual(ns[0].confidence,0.)
        self.assertIn('confidence_unavailable',ns[0].flags)

    def test_missing_external_paths_actionable(self):
        with self.assertRaises(EstimatorUnavailable):
            model_identity('game')

    def test_game_csv_preserves_fractional_pitch_and_timing(self):
        # Contract stub only; actual pretrained validation is separately measured.
        from types import SimpleNamespace
        from src.audio_processor import ingest
        import soundfile as sf
        import numpy as np
        audio=self.root/'source.wav';sf.write(audio,np.ones(22050)*.1,22050)
        repo=self.root/'upstream';repo.mkdir();(repo/'infer.py').write_text('# fixture')
        weights=repo/'model.pt';weights.write_bytes(b'fixture')
        def run(args,**kwargs):
            self.assertEqual(args[args.index('--pitch-format')+1],'number')
            output=Path(args[args.index('--output-dir')+1])
            (output/'input.csv').write_text('onset,offset,pitch\n0.123,0.789,64.37\n',encoding='utf-8')
            return SimpleNamespace(stdout='stub',stderr='',returncode=0)
        import sys
        with patch('src.note_models.subprocess.run',side_effect=run):
            ns=transcribe_external('game',audio,track([64]*100),sys.executable,repo,weights,self.root/'work')
        self.assertEqual((ns[0].start,ns[0].end,ns[0].pitch),(.123,.789,64.37))
        self.assertIn('confidence_unavailable',ns[0].flags)
