"""Frozen human-reference comparisons. No drafts, tuning/test overlap or model fallback."""
from dataclasses import replace
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import datetime,timezone
from uuid import uuid4
import numpy as np
from .real_metrics import score_reference
from .references import validate_reference,reference_notes
from .schema import AnalysisConfig,notes_from_dicts
from .storage import content_hash,key_for,write_json

REPO=Path(__file__).resolve().parents[1]


def read_manifest(path):
    path=Path(path).resolve();manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('format')!='melolysis-real-evaluation-v1':
        raise ValueError('Use an immutable, reviewed real-reference manifest exported by ReferenceStore')
    groups={};sources={};items=[];identities=set()
    for item in manifest['items']:
        audio=(path.parent/item['audio']).resolve();ref_path=(path.parent/item['reference']).resolve()
        if content_hash(audio)!=item['source_sha256'] or content_hash(ref_path)!=item['reference_sha256']:
            raise ValueError('Audio/reference changed since manifest freeze')
        value=json.loads(ref_path.read_text(encoding='utf-8'));validate_reference(value,require_review=True)
        if value['audio']['content_sha256']!=item['source_sha256'] or value['revision']!=item['revision']:
            raise ValueError('Reference revision/source mismatch')
        if item['split']!=value['split'] or item['song_group']!=value['song_group']:
            raise ValueError('Manifest split/group differs from frozen annotation')
        if value['id'] in identities:
            raise ValueError('Duplicate reference in evaluation manifest')
        identities.add(value['id'])
        for table,k in ((groups,item['song_group']),(sources,item['source_sha256'])):
            if k in table and table[k]!=item['split']:
                raise ValueError('Leakage: source/song/singer group crosses evaluation splits')
            table[k]=item['split']
        items.append((item,value,audio))
    return manifest,items


def resolve_systems(path):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    systems=value['systems'] if isinstance(value,dict) else value
    result=[];seen=set()
    for spec in systems:
        spec=dict(spec)
        if not re.fullmatch(r'[a-z0-9_-]{1,64}',spec['id']) or spec['id'] in seen:
            raise ValueError('Each system needs a unique filesystem-safe id')
        parent=spec.get('resegment_from') or spec.get('refine_from')
        if parent and parent not in seen:
            raise ValueError('Derived systems must name an earlier parent in this same comparison')
        if spec.get('resegment_from') and spec.get('refine_from'):
            raise ValueError('A system cannot refine and resegment simultaneously')
        seen.add(spec['id'])
        AnalysisConfig(**spec.get('config',{}))
        for name in ('python','model_python','model_repo','weights'):
            if spec.get(name):
                spec[name]=str((REPO/spec[name]).resolve())
        result.append(spec)
    return result


def run_inference(system,audio,root,metadata,parent_report=None):
    try:
        import psutil
    except ImportError as exc:
        raise RuntimeError('Install requirements-eval.txt for sampled process memory measurements') from exc
    identifier=key_for([system,content_hash(audio),uuid4().hex])
    directory=Path(root)/'jobs'/identifier;directory.mkdir(parents=True,exist_ok=True)
    result_path=directory/'result.json'
    # A cached JOB is not reused: the real pipeline may reuse its marked stage cache.
    if result_path.exists():
        result_path.unlink()
    job={'audio':str(audio),'system':system,'metadata':metadata,
        'output':str((Path(root)/'models'/system['id']).resolve()),'result':str(result_path.resolve())}
    if system.get('resegment_from') or system.get('refine_from'):
        parent=system.get('resegment_from') or system['refine_from']
        if not re.fullmatch(r'[a-z0-9_-]{1,64}',parent):
            raise ValueError('Invalid parent system')
        if parent_report is None:
            return {'status':'unavailable','error':'Derived analysis requires a successful parent from this exact comparison; previous runs are not substituted','parent':parent}
        job['parent_report']=str(Path(parent_report).resolve())
    write_json(directory/'job.json',job)
    environment={**os.environ,'OMP_NUM_THREADS':'2','MKL_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2',
        'PYTHONIOENCODING':'utf-8','MPLBACKEND':'Agg'}
    python=system.get('python',sys.executable)
    start=time.perf_counter();peak=0;samples=0;timed_out=False
    with (directory/'inference.log').open('w',encoding='utf-8') as log:
        try:
            process=subprocess.Popen([python,'-u',str(REPO/'tools'/'run_analysis_worker.py'),str((directory/'job.json').resolve())],
                cwd=REPO,env=environment,stdout=log,stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except OSError as exc:
            return {'status':'unavailable','error':str(exc),'system':system,'log':str(directory/'inference.log')}
        handle=psutil.Process(process.pid)
        while process.poll() is None:
            try:
                descendants=handle.children(recursive=True)
                rss=sum(p.memory_info().rss for p in [handle,*descendants] if p.is_running())
                peak=max(peak,rss);samples+=1
            except (psutil.NoSuchProcess,psutil.AccessDenied):
                pass
            if time.perf_counter()-start>system.get('timeout_seconds',900):
                timed_out=True
                for child in handle.children(recursive=True):
                    try: child.kill()
                    except psutil.NoSuchProcess: pass
                process.kill();process.wait();break
            time.sleep(.05)
    performance={'wall_seconds':time.perf_counter()-start,'peak_sampled_process_tree_rss_bytes':peak,
        'rss_samples':samples,'sample_interval_seconds':.05,'threads_per_native_runtime':2,
        'scope':'Wall includes worker startup/imports/cache access/exports and external model children; RSS is summed concurrent process-tree resident memory, not exclusive RAM or GPU memory'}
    if timed_out:
        return {'status':'failed','error':'Inference timeout; no substitute model used','performance':performance,'log':str(directory/'inference.log')}
    if not result_path.exists():
        return {'status':'failed','error':f'Worker exited {process.returncode} without an inference result',
            'performance':performance,'log':str(directory/'inference.log')}
    value=json.loads(result_path.read_text(encoding='utf-8'));value.update(performance=performance,
        log=str((directory/'inference.log').resolve()),exit_code=process.returncode)
    write_json(result_path,value)
    return value


def plot_comparison(reference,report,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    start,end=reference['excerpt']['start'],reference['excerpt']['end']
    fig,axes=plt.subplots(2,1,figsize=(13,6),sharex=True,gridspec_kw={'height_ratios':[1,3]})
    waveform=report['waveform'];t=np.arange(len(waveform['min']))*waveform['hop_seconds']
    axes[0].fill_between(t,waveform['min'],waveform['max'],color='.5',alpha=.7)
    axes[0].set_ylabel('Waveform')
    raw=report['raw_pitch'];f=np.array([f or np.nan for f in raw['f0_hz']]);pitch=69+12*np.log2(f/440)
    axes[1].plot(raw['times'],pitch,color='.6',linewidth=.6,label=raw['model'])
    for ns,color,label,shift in ((reference_notes(reference),'#167850','human reference',.11),
        (notes_from_dicts(report['predicted_notes']),'#ba4b37','model prediction',-.11)):
        segments=[[(n.start,n.pitch+shift),(n.end,n.pitch+shift)] for n in ns if n.end>start and n.start<end]
        axes[1].add_collection(LineCollection(segments,colors=color,linewidths=3,label=label))
    for region in reference.get('regions',[]):
        if region['kind']=='uncertain':
            axes[1].axvspan(region['start'],region['end'],color='gold',alpha=.25)
    axes[1].autoscale_view();axes[1].set_xlim(start,end);axes[1].set_ylabel('MIDI pitch / continuous center')
    axes[1].set_xlabel('Original source time (seconds)');axes[1].legend(loc='upper right')
    fig.suptitle(f"{reference['metadata'].get('song','excerpt')} · {reference['annotator']} · {reference['split']}\n"
        'Display bars separated vertically ±0.11 semitones; accuracy uses original pitches',fontsize=10)
    fig.tight_layout();Path(path).parent.mkdir(parents=True,exist_ok=True);fig.savefig(path,dpi=120);plt.close(fig)


def summarize(records):
    output={}
    for system in sorted({r['system'] for r in records}):
        output[system]={}
        for edition in sorted({r.get('edition','manual') for r in records if r['system']==system}):
            rs=[r for r in records if r['system']==system and r.get('edition','manual')==edition and r.get('status')=='scored']
            if not rs: continue
            fields=('onset_only','onset_pitch','onset_pitch_offset')
            output[system][edition]={'excerpts':len(rs),
                **{name+'_macro_f1':float(np.mean([r['notes'][name]['f1'] for r in rs])) for name in fields},
                'mean_interval_total_variation':float(np.mean([r['downstream'].get('interval_total_variation',1.) for r in rs])),
                'reference_notes':sum(r['notes']['reference_notes'] for r in rs),
                'estimated_notes':sum(r['notes']['estimated_notes'] for r in rs)}
            frames=[r['frames'] for r in rs if 'raw_pitch_accuracy_50c' in r['frames']]
            if frames:
                output[system][edition]['frames_macro']={k:float(np.mean([f[k] for f in frames if f.get(k) is not None]))
                    for k in ('voicing_precision','voicing_recall','raw_pitch_accuracy_50c','any_octave_error_on_joint_voiced')
                    if any(f.get(k) is not None for f in frames)}
    return output


def run_comparison(manifest_path,systems_path,output='outputs/real-validation',split='development'):
    if split not in {'development','heldout'}:
        raise ValueError('Choose development or heldout; do not pool tuning and test scores')
    manifest,all_items=read_manifest(manifest_path);systems=resolve_systems(systems_path)
    items=[i for i in all_items if i[0]['split']==split]
    if not items:
        raise ValueError('No reviewed references in requested split')
    root=Path(output).resolve();records=[];runs={};frozen={}
    for system in systems:
        for item,reference,audio in items:
            source=item['source_sha256'];identity=(system['id'],source)
            if identity not in runs:
                print(f"[{split}] {system['id']} -> {audio.name}",flush=True)
                parent=system.get('resegment_from') or system.get('refine_from')
                parent_run=runs.get((parent,source),{})
                runs[identity]=run_inference(system,audio,root,reference.get('metadata',{}),parent_run.get('report_path'))
            run=runs[identity]
            if run['status']!='success':
                records.append({'system':system['id'],'edition':reference['origin'].get('edition','manual'),
                    'source_sha256':source,'reference_id':reference['id'],'status':'model_unavailable',
                    'blocker':run,'substitution':None});continue
            report=json.loads(Path(run['report_path']).read_text(encoding='utf-8'))
            result=score_reference(reference,report)
            result.update(system=system['id'],edition=reference['origin'].get('edition','manual'),
                source_sha256=source,song=reference['metadata'].get('song',audio.stem),
                prediction_id=report['prediction_id'],report_path=run['report_path'],
                provenance=report['provenance'],performance=run['performance'],runtime=run['runtime'])
            plot=root/'comparisons'/split/system['id']/(reference['id']+'-'+report['prediction_id'][:12]+'.png')
            plot_comparison(reference,report,plot);result['comparison_plot']=str(plot)
            records.append(result)
            # Persist progress so interruption never turns a partial result into a completed run.
            write_json(root/(split+'-partial.json'),{'complete':False,'records':records})
    summary=summarize(records)
    value={'format':'melolysis-real-results-v1','complete':True,'dataset':manifest.get('dataset','user-human-references'),
        'split':split,'manifest_sha256':content_hash(manifest_path),'systems_sha256':content_hash(systems_path),
        'reference_count':len(items),'source_count':len({i[0]['source_sha256'] for i in items}),
        'systems':systems,'records':records,'summary':summary,
        'limitations':['Published reference editions scored separately; no best-reference selection',
            'Heldout protects local tuning; overlap with upstream pretrained training is unknown',
            'Frame metrics describe the explicitly named F0 estimator; GAME note inference has separate note metrics',
            'No time-aligned lyric/melisma annotation is invented; unavailable subset metrics stay unavailable']}
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid4().hex[:8]
    value['run_id']=run_id
    value['model_status']={s['id']:{'successful_source_count':len({r['source_sha256'] for r in records if r['system']==s['id'] and r.get('status')=='scored'}),
        'requested_source_count':value['source_count']} for s in systems}
    value['immutable_results_path']=str(root/'results'/split/(run_id+'.json'))
    write_json(root/'results'/split/(run_id+'.json'),value)
    write_json(root/(split+'-results.json'),value)
    lines=[f'# Real vocal comparison — {split}','',f"{value['source_count']} real recordings, {len(items)} reviewed annotation editions.",'',
        '| System | Edition | Excerpts | Onset + pitch F1 | Onset + pitch + offset F1 |','|---|---|---:|---:|---:|']
    for system,editions in summary.items():
        for edition,s in editions.items():
            lines.append(f"| {system} | {edition} | {s['excerpts']} | {s['onset_pitch_macro_f1']:.4f} | {s['onset_pitch_offset_macro_f1']:.4f} |")
    lines+=['','Failures and exact blockers, performance, frame metrics, errors, downstream effects and comparison plot paths are retained in the JSON.']
    (root/(split+'-RESULTS.md')).write_text('\n'.join(lines),encoding='utf-8')
    return value
