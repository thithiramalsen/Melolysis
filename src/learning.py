"""Passage-grounded teaching, independent user ideas and measurable exercise checks.

This module reads existing note events. It does not transcribe, attest references,
train models or infer emotion/harmony/lyrics from a vocal.
"""
from dataclasses import replace
import math
from .features import analyze_notes
from .motifs import discover_motifs,representation,sequence_distance,source_similarity,variation
from .schema import NoteEvent,notes_from_dicts
from .composition import CompositionConfig,SCALES
from .storage import key_for


def evidence(notes):
    return {'start':notes[0].start,'end':notes[-1].end,'note_ids':[n.id for n in notes],
        'intervals':[round(b.pitch-a.pitch,4) for a,b in zip(notes,notes[1:])],
        'durations':[n.duration for n in notes],'contour':[0 if abs(b.pitch-a.pitch)<.5 else (1 if b.pitch>a.pitch else -1) for a,b in zip(notes,notes[1:])]}


def passage_study(report,start,end,context=None):
    start,end=float(start),float(end)
    if not math.isfinite(start+end) or not 0<=start<end<=report['audio']['duration']+1e-6:
        raise ValueError('Choose a positive passage inside the original recording.')
    original=notes_from_dicts(report['notes'])
    notes=[replace(n,start=max(start,n.start),end=min(end,n.end)) for n in original if n.start<end and n.end>start]
    context=context or {};provided=report.get('context',{})
    chords=provided.get('chords');grid=provided.get('beat_grid')
    if context.get('tempo'):
        tempo=float(context['tempo']);origin=float(context.get('origin',start))
        if not 20<=tempo<=300 or not math.isfinite(origin):raise ValueError('Supply a tempo from 20–300 BPM and a finite beat origin.')
        grid={'tempo':tempo,'origin':origin}
    if context.get('progression'):
        if not grid:raise ValueError('Supply a tempo and beat origin to place the chord progression.')
        chords=chord_spans(context['progression'],grid['origin'],grid['tempo'])
    source={'source_hash':report['audio']['content_sha256'],'prediction_id':report['prediction_id'],
        'correction_revision':report['provenance'].get('correction_revision'),
        'song':report['metadata'].get('song','Untitled recording'),'artist':report['metadata'].get('artist',''),
        'note_fingerprint':key_for(report['notes']),'start':start,'end':end,
        'note_edition':'saved working correction' if report['provenance'].get('correction_revision') else 'model prediction'}
    result={'format':'melolysis-study-v1','scope':'single_song_passage','source':source,
        'notes':[n.to_dict() for n in notes],'findings':[],'comparisons':[],
        'limits':['These are observations of this passage, not established artist characteristics.',
            'Transcription errors can change the explanation. Listen to the highlighted evidence.',
            'Phrases are rest-delimited candidates; section and breath boundaries are not independently verified.'],
        'context':{'beat_grid':grid,'chords':chords,'supplied':context},'status':'ready'}
    result['analysis_method']='event-techniques-v2'
    result['id']=key_for({'source':source,'context':result['context'],'version':2})
    if len(notes)<3 or all(n.confidence<.15 and 'confidence_unavailable' not in n.flags for n in notes):
        result.update(status='needs_review',reason='This passage has fewer than three note events or only very low-confidence events. Choose a longer passage or review its transcription.')
        return result
    f=analyze_notes(notes,beat_grid=grid,chords=chords,tonal_context=provided.get('tonal_context'))
    result['features']=f;result['motifs']=discover_motifs(notes)
    result['quality']={'low_confidence_notes':sum(n.confidence<.35 and 'confidence_unavailable' not in n.flags for n in notes),
        'unavailable_confidence_notes':sum('confidence_unavailable' in n.flags for n in notes),
        'short_events_under_120ms':sum(n.duration<.12 for n in notes),
        'clipped_boundary_note_ids':[n.id for n in original if n.start<start<n.end or n.start<end<n.end],
        'confidence_meaning':'Model/voicing confidence is not calibrated annotation correctness.'}
    groups={}
    for n in notes:groups.setdefault(n.phrase,[]).append(n)
    def add(kind,title,text,ns,exercise=None,category='measured_property',extra=None):
        item={'id':key_for([result['id'],kind,[n.id for n in ns]]),'kind':kind,'title':title,'text':text,
            'category':category,'evidence':evidence(ns),'technique':exercise,'conditions':
            'Applies to these extracted targets; confirm by ear. The exercise is a creative suggestion, not an artist rule.'}
        if extra:item.update(extra)
        result['findings'].append(item)
    for phrase,ns in list(groups.items())[:16]:
        if len(ns)<3:continue
        ph=evidence(ns);span=ns[-1].end-ns[0].start;peak=max(ns,key=lambda n:n.pitch);low=min(ns,key=lambda n:n.pitch)
        peak_pos=(peak.start-ns[0].start)/span
        add('phrase_shape',f'Phrase at {ns[0].start:.2f}s: follow its shape',
            f'{len(ns)} targets span {max(n.pitch for n in ns)-min(n.pitch for n in ns):g} semitones. '
            f'The first highest target begins {peak_pos:.0%} through the sounding phrase; the lowest begins at {low.start:.2f}s. '
            f'The ending is {ns[-1].pitch-ns[0].pitch:+g} semitones from the opening.',ns,
            {'type':'shape','title':'Invent a phrase with a deliberate high point','instruction':
             'Draw your own pitches. Choose where the high point arrives and how the phrase ends; keep the structure, not the source intervals.',
             'constraint':{'peak_position_target':round(peak_pos,3)}},extra={'peak_note_id':peak.id,'low_note_id':low.id})
        if peak_pos>=.6:
            add('late_peak','Save the highest target for later',f'The first maximum pitch begins at {peak.start:.2f}s, '
                f'{peak_pos:.0%} through this phrase. Earlier targets stay below it.',ns,
                {'type':'late_peak','title':'Delay your own melodic peak','instruction':'Write at least five original notes. Keep your highest pitch until the final third, then decide whether to release downward.',
                 'constraint':{'min_peak_position':.6}})
        if peak!=ns[0] and peak!=ns[-1] and ns[-1].pitch<peak.pitch-.5:
            add('release','Rise to a high point, then release',f'The target at {peak.start:.2f}s is {peak.pitch-ns[-1].pitch:g} semitones above the final target. '
                'The phrase reaches an interior high point and ends lower.',ns,
                {'type':'release','title':'Reach up, then answer lower','instruction':'Draw an original rising gesture and let its ending sit below an interior peak. Use your own interval sizes and rhythm.',
                 'constraint':{'interior_peak':True,'end_below_peak':True}})
        repeated=[(a,b) for a,b in zip(ns,ns[1:]) if abs(a.pitch-b.pitch)<.5]
        if repeated:
            a,b=repeated[0]
            add('repeated_pitch','One target, more than one attack',f'{len(repeated)} adjacent target pair(s) differ by less than 50 cents. '
                f'The example at {a.start:.2f}–{b.end:.2f}s has durations {a.duration:.2f}s and {b.duration:.2f}s. '
                'Listen for separate attacks: segmentation could instead reflect fragmentation.',[a,b],
                {'type':'repeated_pitch','title':'Repeat a pitch and change the rhythm','instruction':'Start with three or more of your own notes. Repeat a pitch with a new duration, then change the ending.',
                 'constraint':{'min_repeated_transitions':1}})
        intervals=ph['intervals'];steps=sum(.5<=abs(x)<=2.1 for x in intervals)
        if steps>=2:
            add('stepwise','Connect targets with small steps',f'{steps} of {len(intervals)} transitions in this phrase move about one or two semitones. '
                'These are target-to-target movements, not vibrato frames.',ns,
                {'type':'stepwise','title':'Make a connected, step-led line','instruction':'Write your own five-note idea with at least half its moves of one or two semitones. Choose a contrasting ending.',
                 'constraint':{'min_step_fraction':.5}})
        ds=[n.duration for n in ns]
        if max(ds)/min(ds)>=1.8:
            longest=max(ns,key=lambda n:n.duration)
            add('duration_contrast','Give one note more time',f'The longest target lasts {longest.duration:.2f}s at {longest.start:.2f}s, '
                f'{max(ds)/min(ds):.1f}× the shortest. Without a supplied beat grid these are seconds, not claimed note values.',ns,
                {'type':'duration_contrast','title':'Create space with a held target','instruction':'Draw a short original motif. Hold one target at least twice as long as another; leave room to breathe.',
                 'constraint':{'min_duration_ratio':2}})
    for rest in f['rests'][:3]:
        if rest['duration']<.12:continue
        adjacent=[n for n in notes if abs(n.end-rest['start'])<1e-6 or abs(n.start-rest['end'])<1e-6]
        if len(adjacent)==2:add('rest','Space between detected targets',f'There is a {rest["duration"]:.2f}s gap at {rest["start"]:.2f}–{rest["end"]:.2f}s. '
            'This is a gap in detected note targets; listen to distinguish a breath, silence or missing transcription.',adjacent,
            {'type':'rest','title':'Let a rest separate your ideas','instruction':'Create two short original gestures with a deliberate breath-sized gap. Hear how the second enters after silence.',
             'constraint':{'min_rest_beats':.5}})
    # Reuse bounded motif candidates, without promoting approximate matches to facts.
    for family in result['motifs']['families'][:4]:
        a,b=family['occurrences'][:2];left=[n for n in notes if n.id in a['note_ids']];right=[n for n in notes if n.id in b['note_ids']]
        if not left or not right:continue
        comparison={'a':evidence(left),'b':evidence(right),'variation':b['variation'],'distance':b['distance'],
            'label':'Candidate recurrence; listen to confirm meaningful similarity.'}
        result['comparisons'].append(comparison)
        add('motif','Repeat a gesture, then vary it',f'A rhythm-aware relative-interval match links {a["start"]:.2f}–{a["end"]:.2f}s '
            f'with {b["start"]:.2f}–{b["end"]:.2f}s. The matching rule classifies it as {b["variation"].replace("_"," ")}; '
            'this is a candidate similarity, not proof of intentional reuse.',left,
            {'type':'motif','title':'Develop your own short motif','instruction':'Draw an original three- or four-note motif. Repeat it with a changed rhythm or ending. Compare the principle without copying source pitches.',
             'constraint':{'own_motif_then_variation':True}},category='statistical_interpretation',extra={'comparison':comparison})
    if not result['comparisons']:
        valid=[ns for ns in groups.values() if len(ns)>=3]
        if len(valid)>=2:
            a,b=valid[:2];result['comparisons'].append({'a':evidence(a),'b':evidence(b),'variation':'different_note_counts' if len(a)!=len(b) else 'compare_contour_and_rhythm',
                'distance':sequence_distance(representation(a),representation(b)),
                'label':'Phrase comparison, not an established recurring motif.'})
    if chords:
        for item in f.get('harmony',{}).get('interpretation_candidates',[])[:3]:
            i=next(i for i,n in enumerate(notes) if n.id==item['note_id']);ns=notes[max(0,i-1):i+2]
            add('harmony','A possible non-chord connection',f'The user-supplied chord context places the target at {item["start"]:.2f}s outside the chord, '
                f'between stepwise chord targets: {item["label"]}. Meter and spelling still need a musician’s judgment.',ns,
                {'type':'harmony','title':'Step outside a chord, then return','instruction':'Supply your own chords. Place a stepwise non-chord target between chord targets and listen to the resolution.',
                 'constraint':{'passing_tone_candidate':True}},category='musical_interpretation')
    else:result['limits'].append('No chord context supplied: tension, resolution and chord changes are not inferred from the vocal.')
    if context.get('syllables'):
        slots=context['syllables'].split()
        result['lyrics']={'source':'user_aligned_one_slot_per_note','slots':slots,'aligned':len(slots)==len(notes),
            'stress_note_ids':[n.id for n,s in zip(notes,slots) if s.startswith('*')] if len(slots)==len(notes) else [],
            'warning':'User alignment, not lyric recognition. One space-separated syllable per event; * marks user stress. Melisma needs manual alignment.'}
    return result


def chord_spans(text,origin,tempo,meter=(4,4)):
    import re
    roots={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11};result=[]
    for i,label in enumerate(text.split('|')):
        label=label.strip();m=re.fullmatch(r'([A-G])([#b]?)(m|maj7|m7|7)?',label)
        if not m:raise ValueError('Use chord symbols such as C | Am | F | G7 (one 4/4 bar each).')
        root=(roots[m[1]]+{'':0,'#':1,'b':-1}[m[2]])%12;quality=m[3] or ''
        pcs=[root,(root+(3 if quality in ('m','m7') else 4))%12,(root+7)%12]
        if quality in ('7','m7','maj7'):pcs.append((root+(11 if quality=='maj7' else 10))%12)
        result.append({'start':origin+i*(meter[0]*4/meter[1])*60/tempo,'end':origin+(i+1)*(meter[0]*4/meter[1])*60/tempo,'pitch_classes':pcs,'label':label})
    return result


def idea_config(value):
    config=CompositionConfig(**{k:value[k] for k in ('tonic','scale','tempo','low','high','bars','contour','time_signature') if k in value})
    return {'tonic':config.tonic,'scale':config.scale,'tempo':config.tempo,'low':config.low,'high':config.high,
        'bars':config.bars,'time_signature':list(config.time_signature),'contour':config.contour,'feel':value.get('feel','balanced'),
        'variation':value.get('variation','ending'),'lyrics':str(value.get('lyrics',''))[:4000],
        'progression':str(value.get('progression',''))[:1000]}


def idea_notes(values,config):
    if not isinstance(values,list) or len(values)>200:raise ValueError('Use at most 200 melody notes.')
    notes=notes_from_dicts(values);limit=config['bars']*config.get('time_signature',[4,4])[0]*4/config.get('time_signature',[4,4])[1]
    if any(n.end>limit+1e-6 for n in notes):raise ValueError('Keep notes inside the chosen phrase length.')
    return notes


def assess_idea(values,config,technique=None,source_notes=()):
    config=idea_config(config);notes=idea_notes(values,config);checks=[]
    if not notes:return {'checks':[],'similarity':{'status':'insufficient_source_or_candidate_notes'},'message':'Draw your own first notes. No source notes are copied.'}
    p=[n.pitch for n in notes];ints=[b-a for a,b in zip(p,p[1:])];duration=[n.duration for n in notes];peak=max(notes,key=lambda n:n.pitch)
    position=(peak.start-notes[0].start)/(notes[-1].end-notes[0].start)
    def check(label,observed,met):checks.append({'label':label,'observed':observed,'met':bool(met)})
    check('Comfortable range',f'{min(p):g}–{max(p):g} MIDI',all(config['low']<=v<=config['high'] for v in p))
    pcs={(config['tonic']+x)%12 for x in SCALES[config['scale']]}
    check('Chosen scale','rounded targets; bends may be intentional',all(round(v)%12 in pcs for v in p))
    kind=(technique or {}).get('type');c=(technique or {}).get('constraint',{})
    if kind in ('shape','late_peak'):check('Position of first high point',f'{position:.0%} through phrase',position>=c['min_peak_position'] if kind=='late_peak' else abs(position-c.get('peak_position_target',.5))<=.2)
    if kind=='release':check('Interior peak and lower ending',f'ending {p[-1]-max(p):+g} semitones from peak',peak not in (notes[0],notes[-1]) and p[-1]<max(p)-.5)
    if kind=='stepwise':check('At least half the moves are steps',f'{sum(.5<=abs(x)<=2.1 for x in ints)}/{len(ints)} transitions',bool(ints) and sum(.5<=abs(x)<=2.1 for x in ints)/len(ints)>=.5)
    if kind=='offbeat':check('An original offbeat entry','half a quarter beat from a whole beat',any(abs(n.start%1-.5)<.08 for n in notes))
    if kind=='repeated_pitch':check('Repeated target',sum(abs(x)<.5 for x in ints),any(abs(x)<.5 for x in ints))
    if kind=='duration_contrast':check('One target held at least twice as long',f'{max(duration)/min(duration):.1f}×',max(duration)/min(duration)>=2)
    if kind=='rest':check('Deliberate space between gestures','at least half a beat',any(b.start-a.end>=.5 for a,b in zip(notes,notes[1:])))
    if kind=='motif':
        half=len(notes)//2;distance=sequence_distance(representation(notes[:half]),representation(notes[half:])) if half>=3 else None
        check('Own motif followed by a related answer',f'distance {distance:.2f}' if distance is not None else 'Add a second gesture of at least three notes',distance is not None and distance<=.3)
    if config['feel']=='contrast':check('Short / held rhythmic contrast',f'{max(duration)/min(duration):.1f}× duration range',max(duration)/min(duration)>=2)
    shape=config['contour']
    shape_met={'arch':peak not in (notes[0],notes[-1]),'late_peak':position>=.6,
        'rise':p[-1]>p[0],'fall':p[-1]<p[0],'level':max(p)-min(p)<=4}[shape]
    check('Chosen shape: '+shape.replace('_',' '),f'first high point at {position:.0%}; ending {p[-1]-p[0]:+g} semitones from opening',shape_met)
    harmony=None
    if config['progression']:
        harmony=analyze_notes(notes,chords=chord_spans(config['progression'],0,60,config['time_signature']))['harmony']
    if kind=='harmony':
        checks.append({'label':'Own chord context','observed':f'{len(harmony["interpretation_candidates"])} stepwise non-chord connection candidates' if harmony else 'Supply your own chords; source chords are not automatically reused.',
            'met':bool(harmony['interpretation_candidates']) if harmony else None})
    source_groups={}
    for n in notes_from_dicts(source_notes):source_groups.setdefault(n.phrase,[]).append(n)
    similarity=source_similarity(notes,list(source_groups.values()),minimum=4)
    similarity['flagged']=similarity['status']=='assessed' and similarity['similarity']>=.92
    return {'checks':checks,'similarity':similarity,'harmony':harmony,'largest_leap':max([abs(x) for x in ints],default=0),
        'message':'Constraint feedback, not songwriting quality. Short/common patterns can resemble each other; similarity screening does not establish legal originality.',
        'lyric_slots':{'supplied':len(config['lyrics'].split()),'notes':len(notes),'aligned':len(config['lyrics'].split())==len(notes),
            'user_stress_beats':[n.start for n,s in zip(notes,config['lyrics'].split()) if s.startswith('*')] if len(config['lyrics'].split())==len(notes) else [],
            'scope':'User-aligned syllable slots and stresses; not automatic lyric or accent inference.'} if config['lyrics'] else None}


def develop_idea(values,config):
    """Deterministic transformations of user-entered material; never source templates."""
    config=idea_config(config);notes=idea_notes(values,config)
    if len(notes)<3:raise ValueError('Draw at least three of your own motif notes before exploring variations.')
    limit=config['bars']*config.get('time_signature',[4,4])[0]*4/config.get('time_signature',[4,4])[1];result=[]
    # Original material is supplied by the user, not fetched from an artist corpus.
    for kind,label in [('rhythm','Change the rhythm'),('ending','Answer with a new ending'),('repeat','Repeat your motif, vary the answer')]:
        ns=list(notes)
        if kind=='rhythm':
            slots=[(n.start,n.end) for n in ns];ns=[replace(n,end=n.start+(n.duration*(.55 if i%2==0 else .9))) for i,n in enumerate(ns)]
        elif kind=='ending':
            allowed=[p for p in range(config['low'],config['high']+1) if p%12 in {(config['tonic']+s)%12 for s in SCALES[config['scale']]}]
            options=[p for p in allowed if abs(p-ns[-1].pitch)>=1 and abs(p-ns[-2].pitch)<=7]
            if not options:continue
            pitch=min(options,key=lambda p:(abs(p-ns[-1].pitch),p));ns[-1]=replace(ns[-1],pitch=float(pitch))
        else:
            start=ns[0].start;span=ns[-1].end-start;gap=.5;available=limit-start
            factor=min(1.,(available-gap)/(2*span))
            if factor<=0:continue
            first=[replace(n,start=start+(n.start-start)*factor,end=start+(n.end-start)*factor) for n in ns]
            shift=first[-1].end-start+gap
            used={n.id for n in first};second=[]
            for n in first:
                identifier=n.id+'-answer'
                while identifier in used:identifier+='-answer'
                used.add(identifier);second.append(replace(n,id=identifier,start=n.start+shift,end=n.end+shift))
            target=second[-1].pitch+(-2 if second[-1].pitch>=config['high']-2 else 2)
            allowed=[p for p in range(config['low'],config['high']+1) if p%12 in {(config['tonic']+s)%12 for s in SCALES[config['scale']]}]
            second[-1]=replace(second[-1],pitch=float(min(allowed,key=lambda p:abs(p-target))));ns=first+second
        result.append({'kind':kind,'label':label,'notes':[n.to_dict() for n in ns]})
    return result
