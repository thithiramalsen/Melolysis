"""Source-aligned reference scoring, error evidence and downstream sensitivity."""
from dataclasses import replace
import numpy as np
from .evaluation import frame_metrics, match_notes, note_metrics
from .features import analyze_notes
from .motifs import discover_motifs
from .references import reference_notes, validate_reference
from .schema import PitchTrack, notes_from_dicts
from .transcription import assign_phrases


def overlaps(note, region):
    return note.start < region['end'] and note.end > region['start']


def merge_intervals(intervals):
    result=[]
    for a,b in sorted(intervals):
        if result and a<=result[-1][1]:
            result[-1][1]=max(result[-1][1],b)
        else:
            result.append([a,b])
    return result


def slice_track(track, start, end, uncertain):
    indices=[i for i,t in enumerate(track.times) if start<=t<end and not any(r['start']<=t<r['end'] for r in uncertain)]
    fields={k:[getattr(track,k)[i] for i in indices] for k in ('times','f0_hz','voiced','confidence','rms')}
    return PitchTrack(**fields,model=track.model,hop_seconds=track.hop_seconds,timebase=track.timebase)


def distribution_distance(a,b):
    """Total variation on a shared discrete support."""
    keys=set(a)|set(b)
    return float(.5*sum(abs(a.get(k,{}).get('proportion',0)-b.get(k,{}).get('proportion',0)) for k in keys))


def downstream_comparison(reference,predicted,reference_id='reference'):
    # Use the identical rest heuristic on both sides, isolating transcription effects.
    r=assign_phrases([replace(n,pitch=float(round(n.pitch))) for n in reference])
    p=assign_phrases([replace(n,pitch=float(round(n.pitch))) for n in predicted])
    rf,pf=analyze_notes(r),analyze_notes(p)
    if not r or not p:
        return {'status':'insufficient_notes','reference_notes':len(r),'predicted_notes':len(p)}
    def contour(ns):
        return [int(np.sign(b.pitch-a.pitch)) for a,b in zip(ns,ns[1:]) if a.phrase==b.phrase]
    def phrase_spans(f):
        return [x['duration'] for x in f['phrases']]
    motifs_r,motifs_p=discover_motifs(r),discover_motifs(p)
    return {'status':'measured','reference_id':reference_id,
        'pitch_binning':'Nearest MIDI semitone for compositional summaries only; accuracy scoring retains continuous note centers',
        'note_count_delta':len(p)-len(r),
        'interval_total_variation':distribution_distance(rf['interval_distribution'],pf['interval_distribution']),
        'pitch_total_variation':distribution_distance(rf['pitch_distribution'],pf['pitch_distribution']),
        'reference_repeated_note_proportion':rf['repeated_note_proportion'],
        'predicted_repeated_note_proportion':pf['repeated_note_proportion'],
        'reference_stepwise_proportion':rf['stepwise_proportion'],'predicted_stepwise_proportion':pf['stepwise_proportion'],
        'reference_phrase_lengths_seconds':phrase_spans(rf),'predicted_phrase_lengths_seconds':phrase_spans(pf),
        'reference_contour':contour(r),'predicted_contour':contour(p),
        'reference_motifs':motifs_r,'predicted_motifs':motifs_p,
        'style_summary_delta':{'stepwise':None if rf['stepwise_proportion'] is None or pf['stepwise_proportion'] is None else pf['stepwise_proportion']-rf['stepwise_proportion'],
            'repeated_notes':None if rf['repeated_note_proportion'] is None or pf['repeated_note_proportion'] is None else pf['repeated_note_proportion']-rf['repeated_note_proportion'],
            'phrase_count':pf['phrase_count']-rf['phrase_count']},
        'interpretation':'Sensitivity to transcription, not proof of artist style; same rest rule applied to both editions'}


def error_analysis(reference,predicted):
    matched=match_notes(reference,predicted)
    rids,pids={a for a,b in matched},{b for a,b in matched}
    missed=[r.to_dict() for i,r in enumerate(reference) if i not in rids]
    extra=[p.to_dict() for j,p in enumerate(predicted) if j not in pids]
    fragments=[];merged=[];octaves=[]
    for r in reference:
        ps=[p for p in predicted if p.start<r.end and p.end>r.start and abs(p.pitch-r.pitch)<=.5]
        if len(ps)>1:
            fragments.append({'reference_note':r.id,'start':r.start,'end':r.end,'predicted_notes':[n.id for n in ps]})
        near=[p for p in predicted if abs(p.start-r.start)<=.05 and 11.5<=abs(p.pitch-r.pitch)<=12.5]
        if near:
            octaves.append({'reference_note':r.id,'start':r.start,'reference_pitch':r.pitch,
                           'predictions':[n.to_dict() for n in near]})
    for p in predicted:
        rs=[r for r in reference if r.start<p.end and r.end>p.start and min(r.end,p.end)-max(r.start,p.start)>.5*r.duration]
        if len(rs)>1:
            merged.append({'prediction':p.id,'start':p.start,'end':p.end,'reference_notes':[n.id for n in rs]})
    return {'missed_notes':missed,'unmatched_predictions':extra,'fragmentation_candidates':fragments,
        'merged_note_candidates':merged,'onset_aligned_octave_errors':octaves,
        'definitions':'Missed/unmatched use onset+pitch matching; fragmentation/merger are overlap diagnostics, not human error labels'}


def score_reference(value, report, require_review=True):
    validate_reference(value,require_review=require_review)
    if report['audio']['content_sha256']!=value['audio']['content_sha256']:
        raise ValueError('Prediction and reference belong to different source audio')
    start,end=value['excerpt']['start'],value['excerpt']['end']
    uncertain=[r for r in value.get('regions',[]) if r['kind']=='uncertain']
    full_reference=reference_notes(value)
    all_predicted=notes_from_dicts(report['predicted_notes'])  # never active human corrections
    full_predicted=[n for n in all_predicted if start<=n.start<end]
    reference=[n for n in full_reference if not any(overlaps(n,r) for r in uncertain)]
    predicted=[n for n in full_predicted if not any(overlaps(n,r) for r in uncertain)]
    uncertainty_seconds=sum(b-a for a,b in merge_intervals([(r['start'],r['end']) for r in uncertain]))
    result={'status':'scored' if reference else 'no_scorable_reference_notes',
        'reference_id':value['id'],'reference_revision':value['revision'],'split':value['split'],
        'excerpt':value['excerpt'],'annotation_origin':value['origin'],'review':value['review'],
        'coverage':{'excerpt_seconds':end-start,'excluded_uncertain_seconds':uncertainty_seconds,
            'excluded_time_fraction':uncertainty_seconds/(end-start),'excluded_reference_notes':len(full_reference)-len(reference),
            'excluded_predicted_notes':len(full_predicted)-len(predicted),
            'mask_rule':'Exclude any event overlapping an uncertain source interval; report exclusions and unmasked scores too'},
        'notes':note_metrics(reference,predicted),'unmasked_notes':note_metrics(full_reference,full_predicted),
        'errors':error_analysis(reference,predicted),
        'downstream':downstream_comparison(reference,predicted,value['id'])}
    raw=PitchTrack(**report['processed_pitch'])
    if value.get('pitch'):
        truth=slice_track(PitchTrack(**value['pitch']),start,end,uncertain)
        result['frames']=frame_metrics(truth,raw)
        # Standard RPA on the common voiced subset, reported separately from recall.
        t=np.array(truth.times); et=np.array(raw.times)
        if len(t) and len(et):
            idx=np.searchsorted(et,t).clip(0,len(et)-1);left=np.maximum(0,idx-1)
            idx=np.where(abs(et[left]-t)<=abs(et[idx]-t),left,idx)
            rf=np.array([f or np.nan for f in truth.f0_hz]);ef=np.array([f or np.nan for f in raw.f0_hz])[idx]
            both=np.array(truth.voiced,dtype=bool)&np.array(raw.voiced,dtype=bool)[idx]&np.isfinite(rf)&np.isfinite(ef)&(abs(et[idx]-t)<=raw.hop_seconds/2+1e-6)
            cents=1200*np.log2(ef[both]/rf[both]); octave=np.round(cents/1200)
            result['frames']['pitch_accuracy_50c_on_joint_voiced']=float(np.mean(abs(cents)<=50)) if len(cents) else None
            result['frames']['any_octave_error_on_joint_voiced']=float(np.mean((octave!=0)&(abs(cents-octave*1200)<=50))) if len(cents) else None
        result['frames']['reference_kind']='published or manually corrected continuous F0; not derived from notes'
        result['frames']['estimator']=raw.model
    else:
        result['frames']={'status':'unavailable','reason':'No independent continuous F0 labels; symbolic notes are not expressive-pitch ground truth'}
    # Reference-derived repeated pitches are an operational subset, not lyric inference.
    windows=[]
    for a,b in zip(reference,reference[1:]):
        if abs(a.pitch-b.pitch)<=.5 and 0<=b.start-a.end<=.5:
            windows.append((max(start,a.start-.05),min(end,b.end+.05)))
    def subset(windows):
        if not windows:
            return {'status':'unavailable','reason':'No labeled/reference-defined target events'}
        included=lambda n:any(a<=n.start<b for a,b in windows)
        return {'status':'scored','windows':windows,
                'notes':note_metrics([n for n in reference if included(n)],[n for n in predicted if included(n)])}
    result['repeated_pitch_subset']=subset(merge_intervals(windows))
    result['repeated_pitch_subset']['definition']='Adjacent reference pitches within 50 cents and gaps <=500ms; no new human attack labels inferred'
    melisma=[(r['start'],r['end']) for r in value.get('regions',[]) if r['kind']=='melisma']
    result['melisma_subset']=subset(melisma)
    result['short_note_subset']={'definition':'Reference durations <=180ms; NOT equivalent to human-labeled melismas',
        'reference_notes':sum(n.duration<=.18 for n in reference),
        'recall_onset_pitch':sum(reference[i].duration<=.18 for i,j in match_notes(reference,predicted))/max(1,sum(n.duration<=.18 for n in reference))}
    return result
