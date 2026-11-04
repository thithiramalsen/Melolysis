"""Acoustic-tail regression cases, not fabricated human annotations."""
import unittest
import numpy as np
from src.note_refinement import refine_offsets
from src.schema import NoteEvent,PitchTrack


def contour(voiced,energy):
    n=len(voiced)
    return PitchTrack((np.arange(n)*.01).tolist(),[440.]*n,voiced,[.9]*n,energy,'test-fixture',.01)


class RefinementTests(unittest.TestCase):
    def test_only_fading_unvoiced_tail_is_trimmed(self):
        track=contour([True]*80+[False]*20,[1.]*80+[.05]*20)
        note=NoteEvent('n',0,1,69,0)
        notes,evidence=refine_offsets([note],track)
        self.assertAlmostEqual(notes[0].end,.8)
        self.assertEqual(notes[0].start,note.start)
        self.assertEqual(notes[0].pitch,note.pitch)
        self.assertEqual(note.end,1.)
        self.assertEqual(len(evidence),1)
        self.assertEqual(track.f0_hz,[440.]*100)

    def test_energetic_voicing_dropout_is_not_a_silence_boundary(self):
        track=contour([True]*80+[False]*20,[1.]*100)
        notes,evidence=refine_offsets([NoteEvent('n',0,1,69,0)],track)
        self.assertEqual(notes[0].end,1.)
        self.assertEqual(evidence,[])

    def test_large_or_unreliable_tail_is_reviewed_without_guessing(self):
        track=contour([True]*40+[False]*60,[1.]*40+[0.]*60)
        notes,_=refine_offsets([NoteEvent('n',0,1,69,0)],track)
        self.assertEqual(notes[0].end,1.)
        track=contour([False]*100,[0.]*100)
        notes,_=refine_offsets([NoteEvent('n',0,1,69,0)],track)
        self.assertEqual(notes[0].end,1.)

    def test_repeated_attacks_and_pitch_bends_are_not_resegmented(self):
        track=contour([True]*100,[1.]*100)
        notes=[NoteEvent('a',0,.5,69,0),NoteEvent('b',.5,1.,69,0)]
        after,changes=refine_offsets(notes,track)
        self.assertEqual([(n.start,n.end,n.pitch) for n in after],[(0,.5,69),(.5,1.,69)])
        self.assertEqual(changes,[])

    def test_invalid_refinement_parameters_fail(self):
        with self.assertRaises(ValueError):
            refine_offsets([],contour([],[]),{'tail_energy_ratio':2})
