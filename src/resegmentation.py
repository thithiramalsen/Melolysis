"""Controlled note-segmentation experiments on an immutable, identical F0 estimate."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import time
from .features import analyze_notes
from .motifs import discover_motifs
from .pipeline import export_notes
from .schema import AnalysisConfig,PitchTrack
from .storage import content_hash,key_for,write_json
from .transcription import segment_notes

ALLOWED={'min_note_seconds','transition_seconds','pitch_change_semitones','phrase_rest_seconds'}


def resegment_report(parent_path,output_root,overrides):
    if not overrides or set(overrides)-ALLOWED:
        raise ValueError('Resegmentation may change only note-boundary parameters; no F0 or reference-dependent changes')
    start=time.perf_counter();parent_path=Path(parent_path)
    report=json.loads(parent_path.read_text(encoding='utf-8'))
    config=replace(AnalysisConfig(**report['provenance']['config']),**overrides)
    notes=segment_notes(PitchTrack(**report['processed_pitch']),report['audio']['duration'],config)
    identity=key_for({'parent':report['prediction_id'],'overrides':overrides,
        'segmenter_sha256':content_hash(Path(__file__).with_name('transcription.py')),
        'experiment_sha256':content_hash(__file__)})
    directory=Path(output_root)/'analyses'/report['audio']['content_sha256']/identity
    directory.mkdir(parents=True,exist_ok=True)
    report.update(prediction_id=identity,predicted_notes=[n.to_dict() for n in notes],notes=[n.to_dict() for n in notes])
    from dataclasses import asdict
    report['provenance']={**report['provenance'],'config':asdict(config),
        'note_model':{'name':'heuristic-resegmented','runtime':'controlled-boundary-study-v1'},
        'correction_revision':None,'correction_base_prediction':None,
        'parent_prediction_id':json.loads(parent_path.read_text(encoding='utf-8'))['prediction_id'],
        'parent_report_sha256':content_hash(parent_path),'resegmentation_overrides':overrides,
        'f0_reestimated':False}
    context=report.get('context',{})
    report['features']=analyze_notes(notes,PitchTrack(**report['raw_pitch']),context.get('beat_grid'),context.get('chords'),context.get('tonal_context'))
    report['motifs']=discover_motifs(notes)
    report['runtime']={'seconds':time.perf_counter()-start,'pitch_cache_hit':True,'note_cache_hit':False,
        'scope':'Segmentation/features/exports only; parent F0 inference excluded'}
    export_notes(notes,directory/'notes.csv',directory/'notes.mid')
    if (parent_path.parent/'playback.wav').exists():
        shutil.copyfile(parent_path.parent/'playback.wav',directory/'playback.wav')
    report['report_path']=str((directory/'report.json').resolve())
    write_json(directory/'report.json',report)
    if not (directory/'prediction.json').exists():
        write_json(directory/'prediction.json',{'prediction_id':identity,'audio':report['audio'],
            'provenance':report['provenance'],'raw_pitch':report['raw_pitch'],'notes':report['predicted_notes']})
    return report
