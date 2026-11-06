"""M0 migration and snapshot contracts on disposable reports only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from src.workspace import Workspace
from src.storage import write_json, content_hash


class CatalogTests(unittest.TestCase):
    def setUp(self):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir='.cache/tests'); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.app=Workspace(self.root)
        self.sources=[]
        for index in range(3):
            audio=self.root/f'audio{index}.wav';audio.write_bytes(bytes([index])*10)
            source=content_hash(audio);self.sources.append(source)
            for version in range(2 if index==0 else 1):
                row=dict(audio=dict(content_sha256=source,source_path=str(audio.resolve()),duration=3),
                    metadata=dict(song='Same unconfirmed filename',artist='Unconfirmed singer'),
                    prediction_id=f'p{version}',provenance=dict(note_model=dict(name='test'),config={}),
                    raw_pitch=dict(model='test'),notes=[dict(id='n',start=0,end=1,pitch=60,confidence=.9)])
                write_json(self.root/'analyses'/source/str(version)/'report.json',row)
        self.original={str(p):content_hash(p) for p in self.root.rglob('*') if p.is_file()}

    def save(self,source,**kw):
        return self.app.dispatch('catalog-reconcile',dict(source_hash=source,
            base_revision=self.app.identities.current()['revision'],**kw))

    def test_read_and_dry_run_never_migrate_legacy_files_or_infer_names(self):
        c=self.app.dispatch('catalog-get',{})
        self.assertEqual(c['counts'],dict(recordings=3,works=0,unresolved_recordings=3))
        self.assertEqual(c['artists'],{});self.assertEqual(c['works'],{})
        ids=[g['recording_id'] for g in c['recordings']]
        self.assertEqual(ids,[g['recording_id'] for g in self.app.identities.view()['recordings']])
        preview=self.save(self.sources[0],new_artist='Singer',new_work='Work',dry_run=True)
        self.assertFalse(preview['writes']);self.assertEqual(preview['after']['works'],1)
        self.assertFalse(self.app.identities.root.exists())
        self.assertEqual(self.original,{str(p):content_hash(p) for p in self.root.rglob('*') if p.is_file()})

    def test_two_takes_one_work_other_work_and_unknown(self):
        a=self.save(self.sources[0],new_artist='Singer',new_work='First work',take='Take 1')
        artist=next(iter(a['artists']));work=next(iter(a['works']))
        a=self.save(self.sources[1],artist_ids=[artist],work_id=work,take='Take 2')
        self.assertEqual(a['counts']['works'],1)
        a=self.save(self.sources[2],artist_ids=[artist],new_work='Second work')
        self.assertEqual(a['counts']['works'],2)
        self.assertEqual(len(next(g for g in a['recordings'] if g['source_hash']==self.sources[0])['editions']),2)
        a=self.save(self.sources[1],artist_ids=[],work_id=None)
        self.assertEqual(a['counts']['unresolved_recordings'],1)
        for p,h in self.original.items():self.assertEqual(content_hash(p),h)
        self.assertEqual(Workspace(self.root).identities.view(),a)

    def test_stale_or_foreign_identifiers_cannot_commit(self):
        self.save(self.sources[0],new_artist='Singer')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.dispatch('catalog-reconcile',dict(source_hash=self.sources[0],base_revision=None))
        before=self.app.identities.current()
        for kw in [dict(artist_ids=['bad']),dict(work_id='bad'),dict(preferred_analysis='bad')]:
            with self.assertRaises(ValueError):self.save(self.sources[0],**kw)
        self.assertEqual(self.app.identities.current(),before)

    def test_snapshot_pins_editions_sections_grid_and_catalog(self):
        source=self.sources[0];a=self.save(source,new_artist='Singer',new_work='Work')
        sections=[dict(id='s',type='chorus',name='Chorus 1',start=0,end=2)]
        self.app.musical_context.save(source,'sections',sections,None,3)
        ids=[g['preferred_analysis'] for g in a['recordings']]
        data=dict(ids=ids,catalog_revision=a['revision'])
        snap=self.app.dispatch('corpus-save',data)
        self.assertEqual(snap,self.app.dispatch('corpus-get',dict(id=snap['id'])))
        pinned=deepcopy(snap)
        self.save(source,new_work='Different work')
        self.app.musical_context.save(source,'grid',dict(tempo=100,origin=0,unit=1,meter=[4,4],swing=1,subdivision=2,confirmed=False),None,3)
        self.assertEqual(self.app.dispatch('corpus-get',dict(id=snap['id'])),pinned)
        self.assertEqual(next(e for e in snap['entries'] if e['source_hash']==source)['context']['sections']['value'],sections)
        with self.assertRaisesRegex(ValueError,'Catalog changed'):self.app.dispatch('corpus-save',data)
        with self.assertRaisesRegex(ValueError,'one analysis'):
            self.app.dispatch('corpus-save',dict(ids=list(self.app.catalog()),catalog_revision=self.app.identities.current()['revision']))

    def test_research_cannot_be_silently_included(self):
        path=next(p for p in self.app.catalog().values() if self.sources[0] in str(p))
        r=json.loads(path.read_text());r['metadata']['dataset']='vocadito';write_json(path,r)
        c=self.app.identities.view();ids=[g['preferred_analysis'] for g in c['recordings']]
        with self.assertRaisesRegex(ValueError,'Research recordings'):
            self.app.dispatch('corpus-save',dict(ids=ids,catalog_revision=None))
        snap=self.app.dispatch('corpus-save',dict(ids=ids,catalog_revision=None,purpose='research'))
        self.assertEqual(snap['purpose'],'research')

    def test_profile_uses_work_ids_even_when_titles_collide(self):
        from src.corpus import profile_artist
        a=self.save(self.sources[0],new_artist='Singer',new_work='Same title')
        artist=next(iter(a['artists']));work=next(iter(a['works']))
        self.save(self.sources[1],artist_ids=[artist],work_id=work)
        self.save(self.sources[2],artist_ids=[artist],new_work='Same title')
        reports=self.app.identities.decorate(list(self.app.identities.reports().values()))
        profile=profile_artist(reports)
        self.assertEqual(profile['songs'],2)
        self.assertEqual(profile['recordings'],3)
        self.assertEqual(profile['aggregation_units'],2)

    def test_changed_snapshot_content_is_rejected(self):
        c=self.app.identities.view()
        snap=self.app.identities.snapshot(dict(ids=[c['recordings'][0]['preferred_analysis']],catalog_revision=None))
        path=self.app.identities.root/'corpora'/(snap['id']+'.json')
        changed=deepcopy(snap);changed['entries'][0]['notes'][0]['pitch']+=1;write_json(path,changed)
        with self.assertRaisesRegex(ValueError,'integrity check'):
            self.app.identities.load_snapshot(snap['id'])
