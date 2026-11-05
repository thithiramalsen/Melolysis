"""Controlled symbolic retrieval checks; not real-vocal/perceptual ground truth."""
import json, random, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.melodic_identity import compare, VERSION


def notes(pitches,scale=1):
    return [dict(id=str(i),start=i*.5*scale,end=(i*.5+.4)*scale,pitch=p,confidence=.9,phrase=0,flags=[]) for i,p in enumerate(pitches)]


def side(ns,h):return dict(notes=ns,source_hash=h,analysis_id=h,song=h,sections={'value':[]},grid={'value':None})


def main():
    rng=random.Random(20261105);records=[];start=time.perf_counter()
    for i in range(40):
        p=[60]
        for _ in range(7):p.append(max(48,min(80,p[-1]+rng.choice([-5,-3,-2,1,2,4,7]))))
        a=notes(p)
        for kind in ['transposed','tempo','inserted','negative','permuted_control']:
            q=[v+5 for v in p]
            if kind=='inserted':q.insert(3,q[2]+1)
            if kind=='negative':q=[rng.randint(48,84) for _ in p]
            if kind=='permuted_control':q=list(p);random.Random(17+i).shuffle(q)
            b=notes(q,1.5 if kind=='tempo' else 1)
            result=compare(side(a,'a'),side(b,'b'))
            expected={(str(j),str(j+(1 if kind=='inserted' and j>=3 else 0))) for j in range(len(p))}
            predicted={(o['a'],o['b']) for o in result['matches'][0]['operations'] if o['a'] and o['b']} if result['matches'] else set()
            records.append({'base':i,'kind':kind,'retrieved':bool(result['matches']),
                            'correct_links':len(predicted&expected) if kind not in ('negative','permuted_control') else None,
                            'predicted_links':len(predicted),'expected_links':len(expected) if kind not in ('negative','permuted_control') else None,
                            'matched_targets':result['matches'][0]['matched_targets'] if result['matches'] else 0})
    summary={k:{'pairs':sum(r['kind']==k for r in records),'retrieved':sum(r['retrieved'] for r in records if r['kind']==k)} for k in ['transposed','tempo','inserted','negative','permuted_control']}
    for kind in ('transposed','tempo','inserted'):
        rows=[r for r in records if r['kind']==kind];tp=sum(r['correct_links'] for r in rows)
        precision=tp/max(1,sum(r['predicted_links'] for r in rows));recall=tp/sum(r['expected_links'] for r in rows)
        summary[kind].update(link_precision=precision,link_recall=recall,link_f1=2*precision*recall/max(1e-12,precision+recall))
    report={'method':VERSION,'seed':20261105,'scope':'controlled symbolic pilot; all settings fixed before this run; no artist identity or human similarity labels',
            'summary':summary,'wall_seconds':time.perf_counter()-start,'records':records}
    path=Path('docs/identity/symbolic-validation.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))

if __name__=='__main__':main()
