"""Disposable synthetic browser fixture server; never reads/writes user annotations."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from http.server import ThreadingHTTPServer
from src.evaluation import synthesize
from src.pipeline import analyze_file
from src.references import ReferenceStore
from src.storage import content_hash,key_for,write_json
from src.workspace import Workspace,make_handler


def fixture():
    root=Path('.cache/editor-tests')/uuid4().hex;root.mkdir(parents=True)
    y,_,_=synthesize({'sequence':[(69,.65,.25),(69,.45,.25),(71,.6,.3),(72,.7,.25),(74,.5,.2),(72,.55,.25)]})
    stereo=resample_poly(y,2,1)
    audio=root/'SYNTHETIC-EDITOR-TEST.wav';sf.write(audio,np.column_stack([stereo,stereo*.8]),44100)
    workspace=root/'workspace'
    r=analyze_file(audio,workspace,metadata={'song':'DISPOSABLE EDITOR FIXTURE','tags':['synthetic-test-only']})
    # A named contract fixture for model-disagreement UI, not a real second-model prediction.
    other=json.loads(json.dumps(r));other['prediction_id']=key_for(['editor-contract-alternative',r['prediction_id']])
    other['provenance']['note_model']={'name':'DISPOSABLE-ALTERNATIVE-STUB-not-inference'}
    other['notes'][0]['pitch']+=1;other['predicted_notes']=other['notes']
    other['notes'][1]['confidence']=0.;other['notes'][1]['flags']=['confidence_unavailable']
    directory=workspace/'analyses'/r['audio']['content_sha256']/other['prediction_id'];directory.mkdir(parents=True)
    other['report_path']=str((directory/'report.json').resolve());write_json(directory/'report.json',other)
    for name in ('playback.wav','notes.csv','notes.mid'):shutil.copyfile(Path(r['report_path']).parent/name,directory/name)
    # Distinct source hashes exercise corpus operations; cloned symbolic events are UI
    # contract fixtures only. They are never ground truth or model benchmarks.
    for index,(name,dataset) in enumerate([('SECOND PERSONAL FIXTURE',None),('THIRD PERSONAL FIXTURE',None),('SIMULATED VOCADITO UI FIXTURE','vocadito')],1):
        sample=root/(name+'.wav');sf.write(sample,np.column_stack([stereo*.8**index,stereo*.6**index]),44100)
        clone=json.loads(json.dumps(r));clone['audio']['source_path']=str(sample.resolve());clone['audio']['content_sha256']=content_hash(sample)
        clone['metadata'].update(song=name,artist='Fixture artist '+str(index))
        clone['provenance']['note_model']={'name':'DISPOSABLE-LIBRARY-STUB-not-inference'}
        if dataset:clone['metadata']['dataset']=dataset
        dest=workspace/'analyses'/clone['audio']['content_sha256']/clone['prediction_id'];dest.mkdir(parents=True)
        clone['report_path']=str((dest/'report.json').resolve());write_json(dest/'report.json',clone)
        for file in ('playback.wav','notes.csv','notes.mid'):shutil.copyfile(Path(r['report_path']).parent/file,dest/file)
    app=Workspace(workspace)
    identifier=next(i for i,p in app.catalog().items() if str(p.resolve())==r['report_path'])
    ref=app.references.create(r,.1,r['audio']['duration']-.1,'SYNTHETIC UI FIXTURE — NOT HUMAN LABELS',
        split='development',song_group='disposable-editor-fixture',seed=True)
    ns=ref['notes'];ns[0]['pitch']+=.37
    ref=app.references.save(ref['id'],ns,[],ref['annotator'],base_revision=ref['revision'])
    info={'analysis':identifier,'reference':ref['id'],'duration':r['audio']['duration'],
        'report_path':r['report_path'],'workspace':str(workspace.resolve()),'audio_path':str(audio.resolve()),
        'audio_sha256':content_hash(audio),'prediction_path':str(Path(r['report_path']).parent/'prediction.json'),
        'prediction_sha256':content_hash(Path(r['report_path']).parent/'prediction.json'),
        'note_ids':[n['id'] for n in r['predicted_notes']],'human_ground_truth':False}
    write_json('.cache/editor-tests/current.json',info)
    return app


if __name__=='__main__':
    app=fixture();server=ThreadingHTTPServer(('127.0.0.1',8772),make_handler(app))
    print('Disposable annotation fixture server: http://127.0.0.1:8772/',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
