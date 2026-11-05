import unittest
from src.melodic_identity import align, compare


def notes(pitches,shift=0,scale=1):
    return [dict(id=str(i),start=i*.5*scale,end=(i*.5+.4)*scale,pitch=p+shift,
                 confidence=.9,phrase=0,flags=[]) for i,p in enumerate(pitches)]


def side(ns,source='a'):
    return dict(notes=ns,source_hash=source,analysis_id=source,song=source,
                sections={'value':[]},grid={'value':None})


class IdentityTests(unittest.TestCase):
    def test_transposition_and_tempo(self):
        a=notes([60,62,65,64,67,62]);b=notes([60,62,65,64,67,62],5,1.5)
        m=align(a,b)
        self.assertEqual(m['matched_targets'],6)
        self.assertEqual(m['transposition_semitones'],5)
        self.assertAlmostEqual(m['time_scale'],1.5)
        self.assertEqual(a[0]['start'],0)

    def test_inserted_target_traceback(self):
        m=align(notes([60,62,65,64,67,62]),notes([65,67,68,70,69,72,67]))
        self.assertGreaterEqual(m['matched_targets'],5)
        self.assertGreaterEqual(m['gap_targets'],1)

    def test_rests_are_visible(self):
        a=notes([60,62,65,64,67,62]);b=notes([60,62,65,64,67,62])
        for i,n in enumerate(b):n['start']+=i*i*.1;n['end']+=i*i*.1
        m=compare(side(a),side(b,'b'))['matches'][0]
        self.assertIn('rhythmic variation',m['transformations'])

    def test_generic_patterns_and_unrelated(self):
        for pitches in ([60]*8,[60,62,64,66,68,70,72,74]):
            self.assertIsNone(align(notes(pitches),notes(pitches,5)))
        self.assertEqual(compare(side(notes([60,62,65,64,67,62])),side(notes([40,52,41,53,42,54]),'b'))['matches'],[])

    def test_embedded_and_source_guard(self):
        a=notes([60,62,65,64,67,62]);b=notes([50,55,65,67,70,69,72,67,58])
        self.assertTrue(compare(side(a),side(b,'b'))['matches'])
        with self.assertRaises(ValueError):compare(side(a),side(b))

    def test_deterministic_immutable(self):
        a,b=side(notes([60,62,65,64,67,62])),side(notes([60,62,65,64,67,62],4),'b')
        before=repr([a,b]);x=compare(a,b)
        self.assertEqual(x,compare(a,b));self.assertEqual(before,repr([a,b]))
