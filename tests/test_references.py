"""Annotation/evaluation invariants. These fixtures are NOT real human ground truth."""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import soundfile as sf
from src.references import ReferenceStore
from src.real_evaluation import read_manifest
from src.real_metrics import score_reference
from src.schema import NoteEvent,PitchTrack
from src.storage import content_hash


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir='.cache/tests');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=ReferenceStore(self.root/'references')
        audio=self.root/'fixture.wav';sf.write(audio,np.zeros(2000),1000)
        self.audio={'source_path':str(audio.resolve()),'content_sha256':content_hash(audio),
            'original_sample_rate':1000,'original_samples':2000,'channels':1,'sample_rate':1000,
            'samples':2000,'duration':2.,'decoder':'test','channel_policy':'test','input_kind':'isolated_vocal'}
        self.ns=[NoteEvent('a',.2,.6,60.,.7),NoteEvent('b',.8,1.2,62.,.7)]
        track=PitchTrack([0.,.1,.2,.3,.4],[None,None,261.625565,261.625565,261.625565],
            [False,False,True,True,True],[0,0,1,1,1],[0,0,1,1,1],'test-only-prediction',.1)
        self.report={'audio':self.audio,'predicted_notes':[n.to_dict() for n in self.ns],
            'notes':[n.to_dict() for n in self.ns],'prediction_id':'fixture-model',
            'processed_pitch':asdict(track),'raw_pitch':asdict(track),'metadata':{'song':'test fixture'}}

    def draft(self,**kwargs):
        return self.store.create(self.report,.1,1.5,'test-fixture-annotator',split='development',seed=True,**kwargs)

    def reviewed(self):
        r=self.draft()
        return self.store.save(r['id'],r['notes'],[],r['annotator'],'test-fixture-reviewer',True,True,r['revision'])

    def test_seed_is_not_ground_truth_and_does_not_change_prediction(self):
        before=json.dumps(self.report,sort_keys=True)
        r=self.draft()
        self.assertEqual(r['review']['status'],'draft')
        self.assertEqual(r['excerpt']['start_sample'],100)
        self.assertEqual(r['notes'][0]['start'],.2)
        self.assertEqual(json.dumps(self.report,sort_keys=True),before)
        with self.assertRaisesRegex(ValueError,'Draft'):
            score_reference(r,self.report)

    def test_review_requires_human_attestation(self):
        r=self.draft()
        with self.assertRaisesRegex(ValueError,'attestation'):
            self.store.save(r['id'],r['notes'],[],r['annotator'],'reviewer',True,False)
        with self.assertRaisesRegex(ValueError,'attestation'):
            self.store.save(r['id'],r['notes'],[],r['annotator'],'',True,True)

    def test_revisions_immutable_and_stale_save_rejected(self):
        r=self.draft();before=self.store.path(r['id'])/(r['revision']+'.json')
        original=before.read_bytes();notes=[dict(n) for n in r['notes']];notes[0]['pitch']=61.
        saved=self.store.save(r['id'],notes,[],r['annotator'],base_revision=r['revision'])
        self.assertEqual(before.read_bytes(),original)
        self.assertNotEqual(r['revision'],saved['revision'])
        with self.assertRaisesRegex(ValueError,'changed'):
            self.store.save(r['id'],notes,[],r['annotator'],base_revision=r['revision'])

    def test_same_source_cannot_leak_between_splits(self):
        self.draft(song_group='group-a')
        with self.assertRaisesRegex(ValueError,'Leakage'):
            self.store.create(self.report,1.5,2.,'fixture',split='heldout',song_group='different-group')

    def test_sample_bounds_and_uncertainty_validation(self):
        r=self.draft()
        with self.assertRaisesRegex(ValueError,'outside'):
            self.store.create(self.report,1.,2.5,'fixture')
        with self.assertRaisesRegex(ValueError,'reason'):
            self.store.save(r['id'],r['notes'],[{'kind':'uncertain','start':.2,'end':.4}],r['annotator'])

    def test_manifest_pins_source_and_annotation_revision(self):
        r=self.reviewed();manifest=self.root/'manifest.json'
        self.store.export_manifest(manifest,[r['id']])
        _,items=read_manifest(manifest);self.assertEqual(items[0][1]['revision'],r['revision'])
        self.store.save(r['id'],r['notes'],[],r['annotator'])
        _,items=read_manifest(manifest);self.assertEqual(items[0][1]['revision'],r['revision'])
        Path(r['audio']['source_path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):
            read_manifest(manifest)

    def test_manifest_refuses_unreviewed_drafts(self):
        r=self.draft()
        with self.assertRaisesRegex(ValueError,'Draft'):
            self.store.export_manifest(self.root/'draft-manifest.json',[r['id']])

    def test_singer_group_cannot_cross_split_even_for_different_audio(self):
        self.draft(song_group='same-singer')
        other=json.loads(json.dumps(self.report));other['audio']['content_sha256']='another-source'
        with self.assertRaisesRegex(ValueError,'Leakage'):
            self.store.create(other,.1,1.5,'fixture',split='heldout',song_group='same-singer')

    def test_melisma_metric_requires_explicit_region(self):
        r=self.reviewed()
        self.assertEqual(score_reference(r,self.report)['melisma_subset']['status'],'unavailable')
        r['regions']=[{'kind':'melisma','start':.1,'end':1.5,'reason':'test label only'}]
        self.assertEqual(score_reference(r,self.report)['melisma_subset']['notes']['onset_pitch']['f1'],1.)

    def test_draft_can_be_assigned_a_split_but_assigned_split_cannot_flip(self):
        r=self.store.create(self.report,.1,1.5,'fixture',seed=True)
        saved=self.store.save(r['id'],r['notes'],[],r['annotator'],split='development',song_group='singer-group')
        self.assertEqual(saved['split'],'development');self.assertEqual(saved['song_group'],'singer-group')
        with self.assertRaisesRegex(ValueError,'cannot change'):
            self.store.save(r['id'],r['notes'],[],r['annotator'],split='heldout')

    def test_uncertainty_reports_coverage_and_unmasked_scores(self):
        r=self.reviewed();r['regions']=[{'kind':'uncertain','start':.19,'end':.61,'reason':'fixture ambiguity'}]
        model=json.loads(json.dumps(self.report));model['predicted_notes'][0]['pitch']=72
        result=score_reference(r,model)
        self.assertEqual(result['notes']['onset_pitch_offset']['f1'],1.)
        self.assertLess(result['unmasked_notes']['onset_pitch_offset']['f1'],1.)
        self.assertEqual(result['coverage']['excluded_reference_notes'],1)
        self.assertGreater(result['coverage']['excluded_time_fraction'],0)

    def test_active_corrections_never_count_as_model_predictions(self):
        r=self.reviewed();model=json.loads(json.dumps(self.report))
        model['notes'][0]['pitch']=80
        result=score_reference(r,model)
        self.assertEqual(result['notes']['onset_pitch_offset']['f1'],1.)
        self.assertEqual(result['frames']['status'],'unavailable')
        self.assertEqual(result['melisma_subset']['status'],'unavailable')

    def test_source_mismatch_and_no_scorable_events_explicit(self):
        r=self.reviewed();model=json.loads(json.dumps(self.report));model['audio']['content_sha256']='wrong'
        with self.assertRaisesRegex(ValueError,'different'):
            score_reference(r,model)
        r['regions']=[{'kind':'uncertain','start':.1,'end':1.5,'reason':'all uncertain'}]
        result=score_reference(r,self.report)
        self.assertEqual(result['status'],'no_scorable_reference_notes')

    def test_downstream_effects_and_repeated_pitch_subset(self):
        r=self.reviewed();r['notes'][1]['pitch']=60
        model=json.loads(json.dumps(self.report));model['predicted_notes'][1]['pitch']=67
        result=score_reference(r,model)
        self.assertEqual(result['repeated_pitch_subset']['status'],'scored')
        self.assertGreater(result['downstream']['interval_total_variation'],0)
        self.assertNotEqual(result['downstream']['reference_contour'],result['downstream']['predicted_contour'])


if __name__=='__main__':
    unittest.main()
