"""Optional, bounded acoustic corroboration for late note offsets; raw predictions survive."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import time
import numpy as np
from .schema import PitchTrack,notes_from_dicts
from .storage import content_hash,key_for,write_json
from .pipeline import export_notes
from .features import analyze_notes
from .motifs import discover_motifs
from .note_models import attach_frames

DEFAULT_TAIL_CONFIG={'min_tail_trim_seconds':.03,'max_tail_trim_seconds':.25,
                     'tail_energy_ratio':.5,'min_voiced_core_seconds':.06}


def refine_offsets(notes,track,config=None):
    c={**DEFAULT_TAIL_CONFIG,**(config or {})}
    if set(c)!=set(DEFAULT_TAIL_CONFIG) or not 0<c['min_tail_trim_seconds']<c['max_tail_trim_seconds']:
        raise ValueError('Invalid bounded tail refinement settings')
    if not 0<c['tail_energy_ratio']<1 or c['min_voiced_core_seconds']<=0:
        raise ValueError('Invalid acoustic evidence thresholds')
    times=np.array(track.times);voiced=np.array(track.voiced,dtype=bool);energy=np.array(track.rms)
    result=[];changes=[]
    for n in notes:
        a,b=np.searchsorted(times,[n.start,n.end]);indices=np.flatnonzero(voiced[a:b])+a
        if len(indices)*track.hop_seconds < c['min_voiced_core_seconds']:
            result.append(n);continue
        last=int(indices[-1]);proposed=min(n.end,float(times[last]+track.hop_seconds))
        trim=n.end-proposed
        tail=energy[last+1:b];core=energy[indices]
        ratio=float(np.median(tail)/max(float(np.median(core)),1e-12)) if len(tail) else 1.
        if c['min_tail_trim_seconds']<=trim<=c['max_tail_trim_seconds'] and ratio<c['tail_energy_ratio'] and proposed-n.start>=.02:
            result.append(replace(n,end=proposed,flags=[*n.flags,'acoustically_trimmed_unvoiced_tail']))
            changes.append({'note_id':n.id,'old_end':n.end,'new_end':proposed,'trim_seconds':trim,
                'tail_to_voiced_energy_ratio':ratio,'evidence':'unvoiced suffix plus fading short-window RMS'})
        else:
            result.append(n)
    return attach_frames(result,track),changes


def refine_report(parent_path,output_root,config=None):
    start=time.perf_counter();parent_path=Path(parent_path)
    parent=json.loads(parent_path.read_text(encoding='utf-8'));report=json.loads(json.dumps(parent))
    track=PitchTrack(**report['processed_pitch'])
    notes,changes=refine_offsets(notes_from_dicts(parent['predicted_notes']),track,config)
    identity=key_for({'parent':parent['prediction_id'],'config':{**DEFAULT_TAIL_CONFIG,**(config or {})},'refiner_sha256':content_hash(__file__)})
    directory=Path(output_root)/'analyses'/report['audio']['content_sha256']/identity;directory.mkdir(parents=True,exist_ok=True)
    rows=[n.to_dict() for n in notes]
    report.update(prediction_id=identity,notes=rows,predicted_notes=rows,
        parent_predicted_notes=parent['predicted_notes'],offset_refinement={'changes':changes,'config':{**DEFAULT_TAIL_CONFIG,**(config or {})}})
    report['provenance']={**parent['provenance'],'note_model':{'name':'acoustic-tail-refinement','parent_model':parent['provenance']['note_model']},
        'parent_prediction_id':parent['prediction_id'],'parent_report_sha256':content_hash(parent_path),
        'correction_revision':None,'correction_base_prediction':None,'refiner_sha256':content_hash(__file__),'f0_reestimated':False}
    context=report.get('context',{})
    report['features']=analyze_notes(notes,PitchTrack(**report['raw_pitch']),context.get('beat_grid'),context.get('chords'),context.get('tonal_context'))
    report['motifs']=discover_motifs(notes);report['runtime']={'seconds':time.perf_counter()-start,'pitch_cache_hit':True,
        'note_cache_hit':False,'scope':'Offset refinement/features/exports only; parent inference excluded'}
    report['report_path']=str((directory/'report.json').resolve())
    export_notes(notes,directory/'notes.csv',directory/'notes.mid')
    if (parent_path.parent/'playback.wav').exists():shutil.copyfile(parent_path.parent/'playback.wav',directory/'playback.wav')
    write_json(directory/'report.json',report)
    if not (directory/'prediction.json').exists():
        write_json(directory/'prediction.json',{'prediction_id':identity,'audio':report['audio'],'provenance':report['provenance'],
            'notes':rows,'parent_predicted_notes':parent['predicted_notes'],'raw_pitch':report['raw_pitch']})
    return report
