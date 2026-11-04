"""Source-backed teaching and independent ideas, using explicit synthetic fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
import pretty_midi
from src.learning import passage_study,assess_idea,develop_idea,chord_spans
from src.schema import NoteEvent
from src.storage import write_json,content_hash
from src.workspace import Workspace


def melody(pitches=(60,62,67,64),start=1.,phrase=0):
    return [NoteEvent(f'{phrase}-{i}',start+i*.6,start+i*.6+.45,float(p),.8,phrase=phrase).to_dict() for i,p in enumerate(pitches)]


def report(notes=None):
    return {'audio':{'duration':20.,'content_sha256':'a'*64},'prediction_id':'b'*64,
        'metadata':{'song':'SYNTHETIC LEARNING TEST','artist':'Fixture singer'},'notes':notes or melody(),
        'provenance':{'correction_revision':None},'context':{}}


class StudyTests(unittest.TestCase):
    def test_observations_have_exact_source_evidence_without_mutating_input(self):
        r=report();before=deepcopy(r);study=passage_study(r,1,4)
        self.assertEqual(r,before);self.assertEqual(study['scope'],'single_song_passage')
        self.assertEqual(study['features']['note_count'],4)
        release=next(f for f in study['findings'] if f['kind']=='release')
        self.assertIn('3 semitones above',release['text']);self.assertEqual(release['evidence']['intervals'],[2,5,-3])
        self.assertEqual(release['evidence']['start'],1.);self.assertEqual(release['evidence']['note_ids'],[n['id'] for n in r['notes']])
        self.assertTrue(all(f['evidence']['note_ids'] and f['category'] for f in study['findings']))
        self.assertIsNone(study['context']['chords']);self.assertTrue(any('not inferred' in s for s in study['limits']))

    def test_clipped_notes_retain_ids_and_source_time_and_report_boundary_limits(self):
        r=report();s=passage_study(r,1.2,2.95)
        self.assertEqual(s['notes'][0]['start'],1.2);self.assertEqual(s['notes'][0]['id'],r['notes'][0]['id'])
        self.assertIn(r['notes'][0]['id'],s['quality']['clipped_boundary_note_ids'])
        self.assertEqual(s['source']['note_fingerprint'],passage_study(r,1,4)['source']['note_fingerprint'])

    def test_no_peak_or_repeat_claim_when_property_is_absent(self):
        s=passage_study(report(melody((60,62,64,65))),1,4)
        kinds={f['kind'] for f in s['findings']}
        self.assertNotIn('release',kinds);self.assertNotIn('repeated_pitch',kinds)
        self.assertIn('late_peak',kinds)

    def test_empty_or_very_low_confidence_regions_have_actionable_state(self):
        self.assertEqual(passage_study(report(),10,12)['status'],'needs_review')
        r=report();r['notes']=[{**n,'confidence':.01} for n in r['notes']]
        self.assertEqual(passage_study(r,1,4)['status'],'needs_review')
        for n in r['notes']:n['flags']=['confidence_unavailable']
        self.assertEqual(passage_study(r,1,4)['quality']['unavailable_confidence_notes'],4)

    def test_phrase_boundaries_do_not_introduce_cross_rest_intervals(self):
        s=passage_study(report(melody((60,62,64),phrase=0)+melody((80,78,76),start=5,phrase=1)),0,8)
        self.assertEqual(s['features']['phrase_count'],2)
        self.assertNotIn('16.0',s['features']['interval_distribution'])
        self.assertEqual(s['comparisons'][0]['label'],'Phrase comparison, not an established recurring motif.')

    def test_motif_candidate_uses_measured_relative_intervals_and_two_distinct_passages(self):
        ns=melody((60,62,65,64),phrase=0)+melody((65,67,70,69),start=5,phrase=1)
        s=passage_study(report(ns),0,8);f=next(f for f in s['findings'] if f['kind']=='motif')
        self.assertEqual(f['category'],'statistical_interpretation');self.assertEqual(f['comparison']['variation'],'transposed_repetition')
        self.assertEqual(f['comparison']['a']['intervals'],[2,3,-1]);self.assertEqual(f['comparison']['b']['intervals'],[2,3,-1])

    def test_chord_and_lyric_relationships_require_explicit_context(self):
        s=passage_study(report(melody((60,62,64,65))),0,4,{'tempo':60,'origin':0,'progression':'C','syllables':'*one two three four'})
        self.assertTrue(any(f['kind']=='harmony' for f in s['findings']));self.assertTrue(s['lyrics']['aligned'])
        self.assertEqual(s['lyrics']['stress_note_ids'],['0-0'])
        with self.assertRaisesRegex(ValueError,'tempo'):passage_study(report(),0,4,{'progression':'C'})
        with self.assertRaisesRegex(ValueError,'chord symbols'):chord_spans('made up',0,100)
        self.assertEqual(chord_spans('Am | G7',0,120)[1]['start'],2.)

    def test_bounds_and_nonfinite_values_rejected(self):
        for a,b in [(0,21),(3,2),(-1,2),(0,float('nan'))]:
            with self.assertRaises(ValueError):passage_study(report(),a,b)


class IdeaTests(unittest.TestCase):
    def test_transformations_only_operate_on_user_material_and_preserve_input(self):
        ns=melody((60,64,67),start=0);before=deepcopy(ns)
        variants=develop_idea(ns,{'bars':2});self.assertEqual(ns,before)
        self.assertEqual([v['kind'] for v in variants],['rhythm','ending','repeat'])
        self.assertEqual(len(variants[2]['notes']),6);self.assertEqual([n['pitch'] for n in variants[0]['notes']],[n['pitch'] for n in ns])
        self.assertNotEqual(variants[1]['notes'][-1]['pitch'],ns[-1]['pitch'])
        self.assertTrue(all(n['end']<=8 for v in variants for n in v['notes']))
        twice=develop_idea(variants[2]['notes'],{'bars':2})[-1]['notes']
        self.assertEqual(len(twice),12);self.assertEqual(len({n['id'] for n in twice}),12)
        self.assertTrue(all(n['end']<=8 for n in twice))

    def test_resemblance_detects_transposed_copies_and_reports_short_sequences_unassessed(self):
        source=melody();candidate=[{**n,'pitch':n['pitch']+5} for n in source]
        result=assess_idea(candidate,{'bars':2},source_notes=source)
        self.assertTrue(result['similarity']['flagged']);self.assertEqual(result['similarity']['similarity'],1)
        self.assertEqual(assess_idea(candidate[:3],{'bars':2},source_notes=source)['similarity']['status'],'insufficient_source_or_candidate_notes')

    def test_technique_feedback_is_measured_and_changes_with_edit(self):
        ns=melody((60,62,67,64),start=0);t={'type':'release','constraint':{'interior_peak':True,'end_below_peak':True}}
        self.assertTrue(assess_idea(ns,{'bars':2},t)['checks'][-1]['met'])
        ns[-1]['pitch']=69.;self.assertFalse(assess_idea(ns,{'bars':2},t)['checks'][-1]['met'])
        with self.assertRaisesRegex(ValueError,'phrase length'):assess_idea(melody(start=5),{'bars':1})


class LearningPersistenceTests(unittest.TestCase):
    def setUp(self):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True);self.tmp=tempfile.TemporaryDirectory(dir='.cache/tests');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.r=report();self.path=self.root/'analyses'/('a'*64)/('b'*64)/'report.json';write_json(self.path,self.r)
        self.app=Workspace(self.root);self.id=next(iter(self.app.catalog()));self.study=self.app.dispatch('melody-study',{'id':self.id,'start':1,'end':4})
        self.finding=next(f for f in self.study['findings'] if f['kind']=='release')

    def payload(self):return {'study_id':self.study['id'],'finding_id':self.finding['id'],'notes':melody((60,62,67,64),start=0),
        'config':{'tempo':90,'bars':2},'title':'SYNTHETIC USER IDEA TEST'}

    def test_bookmark_and_idea_revisions_are_independent_and_export_matches_edited_notes(self):
        sha=content_hash(self.path);p=self.payload();bookmark=self.app.dispatch('technique-save',p)
        saved=self.app.dispatch('idea-save',p);self.assertEqual(saved['link']['source']['prediction_id'],'b'*64)
        p.update(id=saved['id'],base_revision=saved['revision']);p['notes'][-1]['pitch']=65
        edited=self.app.dispatch('idea-save',p);self.assertNotEqual(edited['revision'],saved['revision'])
        old=self.app.dispatch('idea-get',{'id':saved['id'],'revision':saved['revision']});self.assertEqual(old['notes'][-1]['pitch'],64)
        midi=pretty_midi.PrettyMIDI(str(self.root/'learning'/'ideas'/saved['id']/'revisions'/(edited['revision']+'.mid')))
        self.assertEqual(midi.instruments[0].notes[-1].pitch,65)
        self.assertAlmostEqual(midi.instruments[0].notes[1].start,p['notes'][1]['start']*60/90,places=2)
        self.assertEqual(content_hash(self.path),sha);self.assertEqual(len(self.app.dispatch('technique-list',{})),1)
        self.assertFalse((self.root/'references').exists());self.assertFalse((self.root/'corrections').exists())

    def test_stale_saves_and_invalid_source_links_rejected(self):
        p=self.payload();saved=self.app.dispatch('idea-save',p)
        with self.assertRaisesRegex(ValueError,'changed'):self.app.dispatch('idea-save',{**p,'id':saved['id'],'base_revision':'old'})
        with self.assertRaisesRegex(ValueError,'technique'):self.app.dispatch('idea-save',{**p,'finding_id':'fake'})
        with self.assertRaisesRegex(ValueError,'identifier'):self.app.dispatch('idea-get',{'id':'../references'})

    def test_study_snapshot_survives_later_transcription_change(self):
        original=self.app.dispatch('melody-study-load',{'id':self.study['id']})
        self.r['notes'][0]['pitch']=59;write_json(self.path,self.r)
        later=self.app.dispatch('melody-study',{'id':self.id,'start':1,'end':4})
        self.assertNotEqual(later['id'],original['id']);self.assertEqual(self.app.dispatch('melody-study-load',{'id':original['id']})['notes'][0]['pitch'],60)

    def test_optional_attempt_feedback_uses_intended_tempo_and_explicit_onset_alignment(self):
        p=self.payload();saved=self.app.dispatch('idea-save',p)
        self.r['notes']=[{**n,'start':.5+n['start']*60/90,'end':.5+n['end']*60/90} for n in p['notes']]
        write_json(self.path,self.r)
        result=self.app.dispatch('idea-attempt',{'idea_id':saved['id'],'analysis_id':self.id})
        self.assertEqual(result['metrics']['onset_pitch_offset']['f1'],1.)
        self.assertEqual(result['contour']['ordered_direction_agreement'],1.)
        self.assertIn('First onsets aligned',result['alignment']);self.assertIn('not songwriting quality',result['scope'])
