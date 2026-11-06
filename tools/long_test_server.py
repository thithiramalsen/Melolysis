"""232-second synthetic UI contract fixture, not inference or human reference data."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.editor_test_server import fixture
from src.storage import write_json,content_hash,key_for
import numpy as np
import soundfile as sf
from http.server import ThreadingHTTPServer
from src.workspace import make_handler

app=fixture()
info=json.loads(Path('.cache/editor-tests/current.json').read_text())
r=json.loads(Path(info['report_path']).read_text())
audio=app.root.parent/'LONG-SYNTHETIC-232s.wav'
y,sr=sf.read(info['audio_path']);sf.write(audio,np.tile(y,(int(np.ceil(232/(len(y)/sr))),1))[:232*sr],sr)
period=r['audio']['duration'];source=content_hash(audio)
r['audio'].update(source_path=str(audio.resolve()),content_sha256=source,duration=232,original_samples=232*sr,samples=232*r['audio']['sample_rate'])
r['metadata']['song']='LONG SYNTHETIC 232s (UI fixture only)'
base=r['notes'];r['notes']=[{**n,'id':n['id']+'-'+str(k),'start':n['start']+k*period,'end':n['end']+k*period,'phrase':k} for k in range(int(232/period)) for n in base]
for channel in ['min','max']:r['waveform'][channel]=(r['waveform'][channel]*int(np.ceil(232/period)))[:int(np.ceil(232/r['waveform']['hop_seconds']))]
r['predicted_notes']=r['notes']
directory=app.root/'analyses'/source/r['prediction_id'];directory.mkdir(parents=True)
r['report_path']=str((directory/'report.json').resolve());write_json(directory/'report.json',r)
import shutil
shutil.copyfile(audio,directory/'playback.wav')
identifier=key_for(str((directory/'report.json').relative_to(app.root)))
write_json('.cache/long-fixture.json',dict(id=identifier,root=str(app.root),audio=str(audio),source=source))
print('Long fixture: http://127.0.0.1:8773',flush=True)
ThreadingHTTPServer(('127.0.0.1',8773),make_handler(app)).serve_forever()
