"""Source grouping and corpus policy; no user data or model changes."""
from copy import deepcopy
import unittest
from src.library import recording_groups,source_category,validate_corpus_sources


def row(identifier='baseline',source='a',**metadata):
    return {'id':identifier,'audio':{'content_sha256':source,'source_path':'C:/vocals/song.wav','duration':20.},
        'metadata':{'artist':'Singer','song':'Song',**metadata},'model':{'name':'heuristic'},
        'estimator':'pyin','correction_revision':None}


class LibraryTests(unittest.TestCase):
    def test_hash_groups_versions_without_merging_references_or_working_editions(self):
        a=row();b=row('game');b['model']['name']='GAME';b['correction_revision']='working1'
        refs=[{'id':i,'revision':'r'+i,'audio':a['audio'],'annotator':i,'review':{'status':'draft'},
               'excerpt':{'start':.5,'end':6.5},'origin':{'kind':'model_assisted_draft'},'split':'development'} for i in ('one','two')]
        original=deepcopy([a,b,refs]);groups=recording_groups([b,a],refs)
        self.assertEqual(len(groups),1);self.assertEqual(groups[0]['analysis_ids'],['baseline','game'])
        self.assertEqual([r['id'] for r in groups[0]['references']],['one','two'])
        self.assertEqual(groups[0]['working_revision'],'working1');self.assertEqual([a,b,refs],original)

    def test_distinct_audio_with_same_song_name_remains_distinct_recordings(self):
        groups=recording_groups([row(),row('second','b')])
        self.assertEqual(len(groups),2);self.assertEqual(groups[0]['song_key'],groups[1]['song_key'])

    def test_research_from_provenance_published_reference_and_legacy_path(self):
        self.assertEqual(source_category(row(dataset='vocadito'))[0],'research')
        self.assertEqual(source_category(row(),[{'origin':{'kind':'published_human_dataset','dataset':'vocadito'}}]),('research','vocadito'))
        legacy=row();legacy['audio']['source_path']='D:\\data\\vocadito\\s.wav'
        self.assertEqual(source_category(legacy)[0],'research')
        # A title containing a dataset name alone is not source provenance.
        self.assertEqual(source_category(row(song='My song about Vocadito'))[0],'personal')

    def test_research_policy_requires_boolean_opt_in_and_counts_unique_audio(self):
        research=row(dataset='vocadito')
        for opt_in in (False,None,'true',1):
            with self.assertRaisesRegex(ValueError,'Research recordings'):
                validate_corpus_sources([research],allow_research=opt_in)
        reports,scope=validate_corpus_sources([research,deepcopy(research)],allow_research=True)
        self.assertEqual(len(reports),1);self.assertTrue(scope['research_opt_in'])
        self.assertEqual(scope['categories'],{'research':1})

    def test_other_model_metadata_cannot_bypass_source_research_category(self):
        personal=row();other=row('alternative',dataset='vocadito')
        self.assertEqual(recording_groups([personal,other])[0]['category'],'research')
        with self.assertRaisesRegex(ValueError,'Research recordings'):
            validate_corpus_sources([personal],context_reports=[personal,other])

    def test_published_reference_matches_content_hash_only(self):
        reference={'audio':{'content_sha256':'b'},'origin':{'kind':'published_human_dataset','dataset':'vocadito'}}
        reports,scope=validate_corpus_sources([row()],references=[reference])
        self.assertEqual(scope['categories'],{'personal':1})
        with self.assertRaisesRegex(ValueError,'Research recordings'):
            validate_corpus_sources([row(source='b')],references=[reference])
