import unittest
from dataclasses import replace
from pathlib import Path
import tempfile
import numpy as np
from src.schema import AnalysisConfig, NoteEvent, PitchTrack, notes_from_dicts
from src.transcription import segment_notes
from src.pitch import postprocess, estimate_chunked
from src.storage import StageCache, latest_correction, save_correction
from src.evaluation import note_metrics, legacy_segment


def track(pitches, rms=None, confidence=None):
    p = np.asarray(pitches, dtype=float)
    valid = np.isfinite(p)
    return PitchTrack((np.arange(len(p))*.01).tolist(),
        [float(440*2**((x-69)/12)) if v else None for x, v in zip(p, valid)], valid.tolist(),
        confidence if confidence is not None else valid.astype(float).tolist(),
        rms if rms is not None else valid.astype(float).tolist(), "test", .01)


class SegmentationTests(unittest.TestCase):
    def test_rest_preserves_repeated_pitch(self):
        t = track([69]*40+[np.nan]*50+[69]*40)
        notes = segment_notes(t, 1.3)
        self.assertEqual(len(notes), 2)
        self.assertAlmostEqual(notes[0].end, .4)
        self.assertAlmostEqual(notes[1].start, .9)
        self.assertEqual(notes[1].phrase, 1)
        self.assertEqual(notes[1].frame_start, 90)

    def test_vibrato_not_notes(self):
        p = 69+.65*np.sin(2*np.pi*5.5*np.arange(200)*.01)
        t = track(p)
        self.assertEqual(len(segment_notes(t, 2.)), 1)
        self.assertGreater(len(legacy_segment(t.f0_hz, .01)), 10)

    def test_legato_step_and_jump(self):
        notes = segment_notes(track([60]*40+[62]*40+[74]*40), 1.2)
        self.assertEqual([n.pitch for n in notes], [60, 62, 74])
        self.assertAlmostEqual(notes[1].start, .4, places=2)

    def test_repeated_attack_without_silence(self):
        rms = np.ones(120)
        rms[39:42] = [.4, .1, .4]
        rms[79:82] = [.4, .1, .4]
        ns = segment_notes(track([67]*120, rms.tolist()), 1.2)
        self.assertEqual(len(ns), 3)

    def test_low_confidence_remains_reviewable(self):
        t = track([69]*100, confidence=[.3]*100)
        ns = segment_notes(t, 1.)
        self.assertIn("review_confidence", ns[0].flags)
        self.assertEqual(t.f0_hz, postprocess(t, AnalysisConfig()).f0_hz)

    def test_scoop_belongs_to_landing_note(self):
        p = np.r_[np.linspace(64, 67, 25), np.full(125, 67)]
        ns = segment_notes(track(p), 1.5)
        self.assertEqual(len(ns), 1)
        self.assertEqual(ns[0].pitch, 67)

    def test_octave_spike_conservative(self):
        t = track([69, 81, 69], confidence=[.9, .3, .9])
        processed = postprocess(t, AnalysisConfig())
        self.assertEqual(processed.flags["suspect_octaves"], [1])
        self.assertAlmostEqual(processed.f0_hz[1], 440)
        self.assertAlmostEqual(t.f0_hz[1], 880)
        sustained = postprocess(track([69]*20+[81]*20+[69]*20), AnalysisConfig())
        self.assertAlmostEqual(sustained.f0_hz[25], 880)

    def test_silence_empty(self):
        self.assertEqual(segment_notes(track([np.nan]*100), 1.), [])
        self.assertEqual(segment_notes(track([]), 0.), [])


class ContractTests(unittest.TestCase):
    def setUp(self):
        Path(".cache/tests").mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=".cache/tests")
        self.addCleanup(self.temp.cleanup)

    def test_invalid_events(self):
        with self.assertRaises(ValueError):
            NoteEvent("x", 1, 0, 60, 1)
        with self.assertRaises(ValueError):
            AnalysisConfig(hop_length=0)
        with self.assertRaises(ValueError):
            notes_from_dicts([NoteEvent("a", 0, 1, 60, 1).to_dict(), NoteEvent("b", .5, 2, 62, 1).to_dict()])

    def test_cache_configuration_changes(self):
        cache = StageCache(self.temp.name)
        cache.put("pitch", {"hop": 220}, {"test": 1})
        self.assertEqual(cache.get("pitch", {"hop": 220}), {"test": 1})
        self.assertIsNone(cache.get("pitch", {"hop": 512}))

    def test_manual_revision_survives_other_model(self):
        ns = [NoteEvent("manual", .1, .5, 62, 1)]
        save_correction(self.temp.name, "source", ns, "model-a")
        c = latest_correction(self.temp.name, "source")
        self.assertEqual(c["notes"][0]["pitch"], 62)
        self.assertEqual(c["base_prediction"], "model-a")

    def test_one_to_one_metrics(self):
        reference = [NoteEvent("a", 0, 1, 60, 1)]
        estimate = [NoteEvent("b", .01, 1, 60, 1), NoteEvent("c", .02, .8, 60, 1)]
        metrics = note_metrics(reference, estimate)
        self.assertEqual(metrics["onset_pitch"]["matches"], 1)
        self.assertAlmostEqual(metrics["onset_pitch"]["f1"], 2/3)

    def test_hop_and_chunk_lattice(self):
        # Fake estimator isolates stitching correctness from expensive inference.
        from unittest.mock import patch
        class Fake:
            def estimate(self, y, sr, c):
                n = int(np.ceil(len(y)/c.hop_length))
                return PitchTrack((np.arange(n)*c.hop_length/sr).tolist(), [440.]*n,
                    [True]*n, [1.]*n, [1.]*n, "fake", c.hop_length/sr)
        c = AnalysisConfig(hop_length=220, chunk_seconds=2.1, context_seconds=.5)
        with patch.dict("src.pitch.ESTIMATORS", {"fake": Fake}):
            t = estimate_chunked(np.zeros(22050*7+17), 22050, replace(c, estimator="fake"))
        self.assertEqual(len(t.times), int(np.ceil((22050*7+17)/220)))
        np.testing.assert_allclose(t.times, np.arange(len(t.times))*220/22050)

    def test_torchcrepe_uses_explicit_native_grid(self):
        from unittest.mock import patch
        class Fake:
            def estimate(self, y, sr, c):
                self_test.assertEqual(sr,16000);self_test.assertEqual(c.hop_length,160)
                count=int(np.ceil(len(y)/160))
                return PitchTrack((np.arange(count)*.01).tolist(),[440.]*count,[True]*count,
                    [1.]*count,[1.]*count,'stub-torch',.01,timebase={'sample_rate':16000,'hop_length':160})
        self_test=self
        with patch.dict('src.pitch.ESTIMATORS',{'torchcrepe':Fake}):
            t=estimate_chunked(np.zeros(22050*4),22050,replace(AnalysisConfig(),estimator='torchcrepe'))
        self.assertEqual(len(t.times),400)
        self.assertAlmostEqual(t.times[-1],3.99)
        self.assertEqual(t.timebase['hop_length'],160)


if __name__ == "__main__":
    unittest.main()
