import unittest
from src.schema import NoteEvent
from src.features import analyze_notes
from src.motifs import discover_motifs, representation, sequence_distance, source_similarity
from src.corpus import profile_artist, songwriting_exercises, assess_attempt
from src.composition import CompositionConfig, generate_candidates


def notes(pitches, start=0., phrase=0, prefix="n", duration=.4):
    return [NoteEvent(f"{prefix}{i}", start+i*duration, start+(i+1)*duration, p, .9, phrase=phrase)
            for i, p in enumerate(pitches)]


def report(ns, source):
    return {"audio": {"content_sha256": source, "source_path": source+".wav"},
            "metadata": {"song": source}, "notes": [n.to_dict() for n in ns],
            "provenance": {}, "motifs": {}}


class AnalysisTests(unittest.TestCase):
    def test_no_interval_across_phrase_rest(self):
        f = analyze_notes(notes([60, 62])+notes([80, 80], 2., 1, "b"))
        self.assertNotIn("18.0", f["interval_distribution"])
        self.assertEqual(f["repeated_note_proportion"], .5)
        self.assertEqual(f["phrase_count"], 2)

    def test_transposed_rhythmic_motif_evidence(self):
        a = notes([60, 62, 65, 64])
        b = notes([67, 69, 72, 71], 3., 1, "b", .5)
        self.assertAlmostEqual(sequence_distance(representation(a), representation(b)), 0)
        motifs = discover_motifs(a+b)
        self.assertEqual(len(motifs["families"]), 1)
        self.assertEqual(motifs["families"][0]["occurrences"][1]["variation"], "transposed_repetition")
        self.assertEqual(discover_motifs(a)["families"], [])

    def test_song_equal_weight_and_dedup(self):
        a = report(notes([60, 62]), "a")
        b = report(notes([60]*100), "b")
        p = profile_artist([a, a, b])
        self.assertEqual(p["songs"], 2)
        self.assertEqual(p["interval_weights"]["2.0"], .5)
        self.assertEqual(p["interval_weights"]["0.0"], .5)
        self.assertIsNone(p["conclusions"][0]["song_bootstrap_95_interval"])

    def test_harmony_only_supplied_context(self):
        ns = notes([60, 62, 64, 67])
        self.assertNotIn("harmony", analyze_notes(ns))
        f = analyze_notes(ns, chords=[{"start": 0, "end": 2, "pitch_classes": [0, 4, 7]}])
        self.assertFalse(f["harmony"]["onset_relationships"][1]["onset_is_chord_tone"])

    def test_multiple_sections_do_not_inflate_song_support(self):
        a = report(notes([60,62]), 'a')
        b = report(notes([60,62,64,65]), 'b')
        b['metadata']['song'] = 'a'
        c = report(notes([60,60]), 'c')
        p = profile_artist([a,b,c])
        self.assertEqual(p['songs'],2)
        self.assertEqual(p['recordings'],3)
        self.assertAlmostEqual(p['conclusions'][0]['equal_song_mean'],.5)

    def test_scale_degrees_require_explicit_tonic(self):
        f = analyze_notes(notes([60,62,64,61]),tonal_context={'tonic_pitch_class':0,'mode':'major'})
        self.assertEqual(f['tonality']['scale_degree_distribution']['chromatic']['count'],1)

    def test_uniform_short_pattern_not_signature(self):
        ns=notes([60,62,64,66])+notes([65,67,69,71],3.,1,'b')
        self.assertEqual(discover_motifs(ns)['families'],[])

    def test_cross_song_motif_has_source_evidence(self):
        a=report(notes([60,62,65,64]),'a')
        b=report(notes([67,69,72,71]),'b')
        p=profile_artist([a,b])
        family=p['cross_song_motifs']['families'][0]
        self.assertEqual(family['support_songs'],2)
        self.assertEqual(family['occurrences'][1]['source_hash'],'b')

    def test_similarity_detects_transposed_copy(self):
        a = notes([60, 62, 64, 65, 67, 64, 62])
        b = notes([65, 67, 69, 70, 72, 69, 67])
        self.assertAlmostEqual(source_similarity(b, [a])["similarity"], 1.)

    def test_composition_determinism_range_and_scale(self):
        c = CompositionConfig(candidates=2, seed=123)
        a, b = generate_candidates({}, c), generate_candidates({}, c)
        self.assertEqual(a, b)
        self.assertEqual(len(a["candidates"]), 2)
        for candidate in a["candidates"]:
            for n in candidate["notes"]:
                self.assertTrue(60 <= n["pitch"] <= 76)
                self.assertIn(n["pitch"] % 12, [0, 2, 4, 5, 7, 9, 11])

    def test_exercise_feedback(self):
        p = profile_artist([report(notes([60, 62, 64, 62]), "a")])
        exercise = songwriting_exercises(p)[0]
        self.assertTrue(assess_attempt(notes([60, 62, 64, 62]), exercise)["checks"]["stepwise"]["met"])

    def test_unrealistic_lyric_density_is_flagged(self):
        result=generate_candidates({},CompositionConfig(bars=1,syllables=96,candidates=1))
        self.assertIn('very_short_notes_below_100ms',result['candidates'][0]['assessment']['review_flags'])
        sparse=generate_candidates({},CompositionConfig(bars=16,syllables=4,candidates=1))
        self.assertEqual(len(sparse['candidates'][0]['notes']),4)
