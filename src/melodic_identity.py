"""Interpretable, source-pinned local note alignment. No inference or audio edits."""
import math
from collections import Counter
from .storage import key_for
from .musical_context import rhythm

VERSION = 'event-local-v1'


def align(a, b):
    """Local event alignment over constant transposition hypotheses, with gaps.

    Return explicit target correspondence, not interval-token correspondence.
    Scores are engineering similarities, never probabilities.
    """
    if len(a) < 4 or len(b) < 4:
        return None
    shifts = Counter(round(y['pitch']-x['pitch'], 1) for x in a for y in b)
    best = None
    for shift, _ in shifts.most_common(8):
        table = [[0.]*(len(b)+1) for _ in range(len(a)+1)]
        back = {}; peak = (0., 0, 0)
        for i, x in enumerate(a, 1):
            for j, y in enumerate(b, 1):
                pitch = min(2., abs(y['pitch']-x['pitch']-shift)/2)
                # Relative duration distinguishes holds; onset/rest differences are
                # measured after traceback so an inserted target does not shift IOIs.
                da = x['end']-x['start']; db = y['end']-y['start']
                ratio = math.log2(db/da)
                cost = .85*pitch + .15*min(1., abs(ratio))
                options = [0., table[i-1][j-1]+.65-cost,
                           table[i-1][j]-.45, table[i][j-1]-.45]
                op = max(range(4), key=options.__getitem__)
                table[i][j] = options[op]; back[i,j] = op
                if options[op] > peak[0]: peak = (options[op], i, j)
        value, i, j = peak; ops = []
        while i and j and table[i][j] > 0:
            op = back[i,j]
            if op == 1:
                ops.append({'a':a[i-1]['id'], 'b':b[j-1]['id'], 'operation':'match',
                            'pitch_delta':b[j-1]['pitch']-a[i-1]['pitch']-shift})
                i-=1; j-=1
            elif op == 2: ops.append({'a':a[i-1]['id'],'b':None,'operation':'omitted_target'}); i-=1
            elif op == 3: ops.append({'a':None,'b':b[j-1]['id'],'operation':'added_target'}); j-=1
            else: break
        ops.reverse(); pairs=[o for o in ops if o['a'] and o['b']]
        if len(pairs)<4: continue
        aa={n['id']:n for n in a}; bb={n['id']:n for n in b}
        pitches=[aa[o['a']]['pitch'] for o in pairs]
        intervals=[round(y-x,1) for x,y in zip(pitches,pitches[1:])]
        # Uniform scales/repeated tones cannot establish an identity motif.
        if len(set(intervals)) < 2: continue
        first,last=pairs[0],pairs[-1]
        span_a=aa[last['a']]['start']-aa[first['a']]['start']
        span_b=bb[last['b']]['start']-bb[first['b']]['start']
        if min(span_a,span_b)<=0: continue
        scale=span_b/span_a
        residuals=[]
        for o in pairs:
            x,y=aa[o['a']],bb[o['b']]
            o['operation']='changed_pitch' if abs(o['pitch_delta'])>.5 else 'match'
            o['a_time']=[x['start'],x['end']];o['b_time']=[y['start'],y['end']]
            o['duration_ratio']=(y['end']-y['start'])/(x['end']-x['start'])/scale
            residuals.append(abs((y['start']-bb[first['b']]['start'])/span_b-(x['start']-aa[first['a']]['start'])/span_a))
        pitch_error=sum(abs(o['pitch_delta']) for o in pairs)/len(pairs)
        gaps=len(ops)-len(pairs)
        strength=value/(.65*max(1,len(ops)))
        candidate={'operations':ops,'transposition_semitones':shift,'time_scale':scale,
                   'strength':strength,'matched_targets':len(pairs),'gap_targets':gaps,
                   'mean_pitch_residual':pitch_error,'onset_shape_error':sum(residuals)/len(residuals)}
        if best is None or candidate['strength']*len(pairs)**.5 > best['strength']*best['matched_targets']**.5:
            best=candidate
    return best


def compare(left, right):
    """Bounded pair search; snapshots have distinct source hashes and pinned editions."""
    if left['source_hash']==right['source_hash']:
        raise ValueError('Choose two distinct recordings; model variants are one source.')
    def windows(side):
        groups={}
        for n in side['notes']:groups.setdefault(n['phrase'],[]).append(n)
        rows=[]
        for group in groups.values():
            for start in range(0,len(group),64):
                w=group[start:start+96]
                if len(w)>=4:rows.append(w)
        return rows
    a,b=windows(left),windows(right); candidates=[]; considered=0
    for x in a[:24]:
        for y in b[:24]:
            considered+=1;m=align(x,y)
            if not m or m['strength']<.62 or m['mean_pitch_residual']>.65:continue
            def occurrence(side, notes, field):
                ids={o[field] for o in m['operations'] if o[field]}
                ns=[n for n in notes if n['id'] in ids]
                start,end=ns[0]['start'],ns[-1]['end']
                return {'source_hash':side['source_hash'],'analysis_id':side['analysis_id'],
                        'song':side['song'],'notes':ns,'start':start,'end':end,
                        'sections':[s for s in side['sections']['value'] if s['start']<end and s['end']>start],
                        'rhythm':rhythm(ns,side['grid']['value'],start,end)}
            m['a']=occurrence(left,x,'a');m['b']=occurrence(right,y,'b')
            m['structural_observations']={}
            for k in ('a','b'):
                o=m[k];ns=o['notes'];peak=max(ns,key=lambda n:n['pitch'])
                m['structural_observations'][k]={
                    'first_peak_fraction':(peak['start']-o['start'])/(o['end']-o['start']),
                    'range_semitones':max(n['pitch'] for n in ns)-min(n['pitch'] for n in ns),
                    'low_confidence_targets':sum(n['confidence']<.35 and 'confidence_unavailable' not in n.get('flags',[]) for n in ns),
                    'unavailable_confidence_targets':sum('confidence_unavailable' in n.get('flags',[]) for n in ns)}
            labels=[]
            if abs(m['transposition_semitones'])>.5:labels.append('transposition')
            if m['onset_shape_error']>.035 or any(abs(math.log2(o.get('duration_ratio',1)))>.35 for o in m['operations']):labels.append('rhythmic variation')
            if m['gap_targets']:labels.append('added/omitted targets — possible ornamentation or transcription error')
            if m['mean_pitch_residual']>.1:labels.append('interval variation')
            m['transformations']=labels or ['near-exact target recurrence']
            m['id']=key_for([m['a'],m['b'],m['operations'],VERSION])
            candidates.append(m)
    candidates.sort(key=lambda m:(-m['matched_targets']*m['strength'],m['id']))
    selected=[]
    for m in candidates:
        if any(all(max(m[k]['start'],s[k]['start'])<min(m[k]['end'],s[k]['end']) for k in ('a','b')) for s in selected):continue
        selected.append(m)
    result={'format':VERSION,'sources':[left,right],'matches':selected[:12],
            'window_pairs':considered,'truncated':len(a)>24 or len(b)>24,
            'scope':'two-recording comparison; independent song and singer identity not established',
            'limitations':['Candidate similarity is not evidence of artist uniqueness or influence.',
                          'Model errors can create or erase correspondences. Scores are not confidence probabilities.',
                          'Added targets are not automatically grace notes or melismas.',
                          'Search is rest-phrase based and bounded; weak/unrelated passages may yield no candidate.']}
    result['id']=key_for(result)
    return result
