"""Archive measured comparisons and generate tables/figures without rerunning inference.

No tuning or model selection happens here. All source plots use the same first
12 seconds; both human editions and all systems remain in the numerical report.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.evaluation import note_metrics
from src.real_evaluation import read_manifest
from src.references import reference_notes
from src.storage import content_hash,write_json

SYSTEMS=['pyin-baseline','torchcrepe-tiny-events','game-small','game-tail-refined']


def mean(values):
    present=[v for v in values if v is not None]
    return float(np.mean(present)) if present else None


def generate(root,destination):
    root,destination=Path(root),Path(destination);destination.mkdir(parents=True,exist_ok=True)
    _,items=read_manifest(root/'vocadito.manifest.json')
    refs={r['id']:r for _,r,_ in items}
    all_results=[]
    for split in ['development','heldout']:
        result=json.loads((root/(split+'-results.json')).read_text(encoding='utf-8'))
        if not result['complete'] or any(s['successful_source_count']!=result['source_count'] for s in result['model_status'].values()):
            raise ValueError('Do not publish an incomplete or partially failed comparison as completed')
        shutil.copyfile(result['immutable_results_path'],destination/(split+'.json'))
        all_results.append(result)
    metrics={'sources':{},'performance':{},'interannotator':{}}
    lines=['# Measured real-vocal tables','',
        'Generated from immutable completed runs; A1 and A2 are scored separately. No best-edition selection.','']
    for result in all_results:
        split=result['split'];records=result['records']
        lines += ['## '+split,'',
            '| System | Edition | Onset P/R/F1 | Onset + pitch P/R/F1 | Full note P/R/F1 | Onset/offset MAE (ms) |',
            '|---|---|---|---|---|---|']
        for system in SYSTEMS:
            for edition in ['A1','A2']:
                rs=[r for r in records if r['system']==system and r['edition']==edition]
                prs=[' / '.join(f"{mean([r['notes'][metric][field] for r in rs]):.4f}" for field in ['precision','recall','f1'])
                     for metric in ['onset_only','onset_pitch','onset_pitch_offset']]
                timing=[mean([r['notes'][key] for r in rs])*1000 for key in ['onset_mae_seconds','offset_mae_seconds']]
                lines.append(f"| {system} | {edition} | {' | '.join(prs)} | {timing[0]:.1f} / {timing[1]:.1f} |")
        lines+=['','Timing errors are conditional on onset+pitch matches. Macro averages give each excerpt equal weight.','',
            '| Track | Human note counts A1/A2 | pYIN full F1 A1/A2 | CREPE Tiny full F1 A1/A2 | GAME full F1 A1/A2 | GAME refined full F1 A1/A2 |',
            '|---|---:|---:|---:|---:|---:|']
        songs=sorted({r['song'] for r in records},key=lambda s:int(s.split('_')[-1]))
        metrics['sources'][split]={}
        for song in songs:
            rs=[r for r in records if r['song']==song]
            example=next(r for r in rs if r['system']==SYSTEMS[0] and r['edition']=='A1')
            a1=refs[example['reference_id']]
            a2=refs[next(r['reference_id'] for r in rs if r['edition']=='A2')]
            agreement=note_metrics(reference_notes(a1),reference_notes(a2))
            metrics['interannotator'][song]=agreement
            counts=[len(a1['notes']),len(a2['notes'])]
            scores=[' / '.join(f"{next(r['notes']['onset_pitch_offset']['f1'] for r in rs if r['system']==s and r['edition']==e):.4f}" for e in ['A1','A2']) for s in SYSTEMS]
            lines.append(f"| [{song}]({song}.png) | {counts[0]} / {counts[1]} | {' | '.join(scores)} |")
            metrics['sources'][split][song]={}
            for system in SYSTEMS:
                edition_results={}
                for edition in ['A1','A2']:
                    r=next(r for r in rs if r['system']==system and r['edition']==edition)
                    edition_results[edition]={'notes':r['notes'],'frames':r['frames'],
                        'repeated_pitch_subset':r['repeated_pitch_subset'],'short_note_subset':r['short_note_subset'],
                        'melisma_subset':r['melisma_subset'],
                        'error_counts':{k:len(r['errors'][k]) for k in ['missed_notes','unmatched_predictions','fragmentation_candidates','merged_note_candidates','onset_aligned_octave_errors']},
                        'downstream':{k:r['downstream'][k] for k in ['interval_total_variation','pitch_total_variation',
                            'style_summary_delta','reference_repeated_note_proportion','predicted_repeated_note_proportion',
                            'reference_phrase_lengths_seconds','predicted_phrase_lengths_seconds']}}
                metrics['sources'][split][song][system]=edition_results
            plot_excerpt(rs,a2,destination/(song+'.png'))
        metrics['performance'][split]={}
        lines+=['','| System | Cold wall seconds: mean / range | Peak sampled summed RSS (MiB) |',
            '|---|---:|---:|']
        for system in SYSTEMS:
            # A1/A2 share one inference: do not double-count model runs.
            rs=[r for r in records if r['system']==system and r['edition']=='A1']
            walls=[r['performance']['wall_seconds'] for r in rs]
            rss=[r['performance']['peak_sampled_process_tree_rss_bytes']/1024**2 for r in rs]
            p={'mean_wall_seconds':mean(walls),'min_wall_seconds':min(walls),'max_wall_seconds':max(walls),
                'max_sampled_summed_rss_mib':max(rss),'inferences':len(rs)}
            metrics['performance'][split][system]=p
            lines.append(f"| {system} | {mean(walls):.2f} / {min(walls):.2f}–{max(walls):.2f} | {max(rss):.1f} |")
        lines+=['','Refined row measures refinement only, excluding parent inference; add GAME cost for end-to-end use.',
            'RSS is sampled process-tree resident memory, not exclusive RAM, allocation peaks, or GPU memory.','']
    lines+=['## Reference disagreement','',
        '| Track | A1 vs A2 onset + pitch F1 | A1 vs A2 full F1 |','|---|---:|---:|']
    for song,agreement in metrics['interannotator'].items():
        lines.append(f"| {song} | {agreement['onset_pitch']['f1']:.4f} | {agreement['onset_pitch_offset']['f1']:.4f} |")
    write_json(destination/'diagnostics.json',metrics)
    (destination/'TABLES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    if (root/'development-short-events.json').exists():
        shutil.copyfile(root/'development-short-events.json',destination/'rejected-short-events.json')
    write_json(destination/'artifact-provenance.json',{
        'archived_runs':{r['split']:{'run_id':r['run_id'],'sha256':content_hash(destination/(r['split']+'.json'))} for r in all_results},
        'dataset_attribution':'Bittner, Pasalo, Bosch, Meseguer Brocal and Rubinstein (2021), vocadito v3, DOI 10.5281/zenodo.5578807, CC-BY-4.0',
        'figures':'Derived displays of published labels/audio waveform and actual model predictions; same first 12 seconds in each comparison',
        'melolysis_human_annotations_authored':0})
    return metrics


def plot_excerpt(records,reference,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    end=min(12.,reference['excerpt']['end']);ref=reference['notes']
    fig,axes=plt.subplots(4,1,figsize=(13,10),sharex=True,sharey=True)
    for ax,system in zip(axes,SYSTEMS):
        r=next(r for r in records if r['system']==system and r['edition']=='A2')
        report=json.loads(Path(r['report_path']).read_text(encoding='utf-8'))
        raw=report['raw_pitch'];freq=np.array([f or np.nan for f in raw['f0_hz']])
        ax.plot(raw['times'],69+12*np.log2(freq/440),lw=.5,color='.65',label='raw expressive F0 ('+r['frames']['estimator']+')')
        for notes,color,label,shift in [(ref,'#167850','published human A2',.12),(report['predicted_notes'],'#b23e32','raw model events',-.12)]:
            segments=[[(n['start'],n['pitch']+shift),(n['end'],n['pitch']+shift)] for n in notes if n['start']<end]
            ax.add_collection(LineCollection(segments,colors=color,linewidths=3,label=label))
        ax.set_title(system,loc='left',fontsize=10);ax.set_ylabel('MIDI pitch');ax.grid(alpha=.15)
        ax.legend(loc='upper right',fontsize=7)
    pitches=[n['pitch'] for n in ref if n['start']<end]
    if pitches:axes[0].set_ylim(min(pitches)-4,max(pitches)+4)
    axes[-1].set_xlim(0,end);axes[-1].set_xlabel('Original audio source seconds')
    fig.suptitle(f"{reference['metadata']['song']} · {reference['split']} · fixed first-12-second display, A2 reference\n"
        'Bars separated vertically: reference +0.12 / prediction −0.12 semitones; scores use unshifted pitches',fontsize=10)
    fig.tight_layout();fig.savefig(path,dpi=120);plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='outputs/real-validation')
    parser.add_argument('--output',default='docs/real-vocal')
    args=parser.parse_args();generate(args.root,args.output)
