"""Editor persistence invariants on disposable synthetic audio, never user references."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
import soundfile as sf
from src.pipeline import analyze_file
from src.storage import content_hash,correction_history
from src.workspace import Workspace


class EditorPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('.cache/tests').mkdir(parents=True,exist_ok=True)
        cls.temp=tempfile.TemporaryDirectory(dir='.cache/tests');cls.base=Path(cls.temp.name)
        audio=cls.base/'synthetic-editor.wav';sr=22050
        sf.write(audio,.2*np.sin(2*np.pi*440*np.arange(sr)/sr),sr)
        cls.report=analyze_file(audio,cls.base/'baseline',metadata={'song':'SYNTHETIC PERSISTENCE TEST ONLY'})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.temp_case=tempfile.TemporaryDirectory(dir=self.base);self.addCleanup(self.temp_case.cleanup)
        self.root=Path(self.temp_case.name);shutil.copytree(self.base/'baseline',self.root/'workspace')
        self.app=Workspace(self.root/'workspace');self.id=next(iter(self.app.catalog()))
        _,self.report=self.app.get_report(self.id)
        self.ref=self.app.references.create(self.report,0.,self.report['audio']['duration'],
            'SYNTHETIC TEST FIXTURE — NOT HUMAN LABELS',split='development',seed=True)

    def test_reference_restore_appends_draft_and_never_restores_attestation(self):
        original=self.app.references.path(self.ref['id'])/(self.ref['revision']+'.json');sha=content_hash(original)
        ns=deepcopy(self.ref['notes']);ns[0]['pitch']+=1
        reviewed=self.app.references.save(self.ref['id'],ns,[],self.ref['annotator'],
            reviewer='TEST ATTESTATION FIXTURE ONLY',reviewed=True,attestation=True,base_revision=self.ref['revision'])
        restored=self.app.dispatch('reference-restore',{'reference_id':self.ref['id'],
            'revision':self.ref['revision'],'base_revision':reviewed['revision']})
        self.assertEqual(restored['notes'],self.ref['notes']);self.assertEqual(restored['review']['status'],'draft')
        self.assertFalse(restored['review']['attestation']);self.assertEqual(content_hash(original),sha)
        self.assertEqual(restored['split'],'development');self.assertEqual(len(self.app.references.history(self.ref['id'])),3)

    def test_stale_reference_restore_does_not_replace_new_work(self):
        current=self.app.references.save(self.ref['id'],self.ref['notes'],[],self.ref['annotator'])
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.references.restore(self.ref['id'],self.ref['revision'],self.ref['revision'])
        self.assertEqual(self.app.references.load(self.ref['id'])['revision'],current['revision'])

    def test_working_revision_restore_does_not_touch_reference_or_raw_prediction(self):
        path,_=self.app.get_report(self.id);prediction=path.parent/'prediction.json';sha=content_hash(prediction)
        raw=deepcopy(self.report['predicted_notes']);ns=deepcopy(raw);ns[0]['pitch']+=1
        first=self.app.dispatch('correct',{'id':self.id,'notes':ns,'base_revision':None})
        one=first['provenance']['correction_revision'];ns[0]['pitch']+=1
        second=self.app.dispatch('correct',{'id':self.id,'notes':ns,'base_revision':one})
        restored=self.app.dispatch('restore-correction',{'id':self.id,'revision':one,
            'base_revision':second['provenance']['correction_revision']})
        self.assertEqual(restored['notes'][0]['pitch'],raw[0]['pitch']+1)
        self.assertEqual(self.app.references.load(self.ref['id'])['revision'],self.ref['revision'])
        self.assertEqual(restored['predicted_notes'],raw);self.assertEqual(content_hash(prediction),sha)
        self.assertEqual(len(correction_history(self.app.root/'corrections',self.report['audio']['content_sha256'])),3)

    def test_stale_working_save_and_restore_are_rejected(self):
        first=self.app.dispatch('correct',{'id':self.id,'notes':self.report['notes'],'base_revision':None})
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.dispatch('correct',{'id':self.id,'notes':self.report['notes'],'base_revision':None})
        with self.assertRaisesRegex(ValueError,'changed'):
            self.app.dispatch('restore-correction',{'id':self.id,'revision':first['provenance']['correction_revision'],'base_revision':None})

    def test_history_identifiers_cannot_escape_reference_store(self):
        with self.assertRaisesRegex(ValueError,'Invalid'):
            self.app.references.history('../corrections')
        with self.assertRaisesRegex(ValueError,'Invalid'):
            self.app.references.restore(self.ref['id'],'../../prediction',self.ref['revision'])


if __name__=='__main__':
    unittest.main()
