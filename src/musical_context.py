"""Independent musical context revisions; never modifies note editions."""
import json, math, re
from uuid import uuid4
from datetime import datetime, timezone
from .storage import write_json, key_for

TYPES={'verse','pre-chorus','chorus','post-chorus','bridge','intro','outro','instrumental','custom'}

def validate_grid(g):
    g=dict(g)
    for k,default in [('tempo',120),('origin',0),('unit',1),('swing',1)]:
        g[k]=float(g.get(k,default))
        if not math.isfinite(g[k]):raise ValueError('Grid values must be finite')
    if not 20<=g['tempo']<=300 or g['unit'] not in (.5,1,1.5,2) or not 1<=g['swing']<=3:raise ValueError('Invalid tempo, pulse unit or swing')
    n,d=g.get('meter',[4,4])
    if type(n)!=int or type(d)!=int or not 1<=n<=12 or d not in (2,4,8,16):raise ValueError('Invalid meter')
    g['meter']=[n,d];g['confirmed']=g.get('confirmed') is True
    return g

def beat(t,g):return (t-g['origin'])*g['tempo']*g['unit']/60

def rhythm(notes,g,start,end):
    if not g:return {'status':'unavailable','reason':'Save and confirm a beat grid for rhythmic findings.'}
    g=validate_grid(g);bar=g['meter'][0]*4/g['meter'][1];pulse=g['unit'];rows=[]
    for n in notes:
        if not start<=n['start']<end:continue
        q=beat(n['start'],g);off=beat(n['end'],g)
        base=math.floor(q/pulse)*pulse;targets=[base,base+pulse*g['swing']/(1+g['swing']),base+pulse]
        target=min(targets,key=lambda v:abs(v-q))
        rows.append({'id':n['id'],'start':n['start'],'end':n['end'],'pitch':n['pitch'],'onset_beats':q,'duration_beats':off-q,'bar':math.floor(q/bar)+1,'within_bar':q%bar,'deviation_beats':q-target,'deviation_ms':(q-target)*60000/(g['tempo']*g['unit']),'confidence':n['confidence'],'crosses_bar':math.floor(q/bar)!=math.floor((off-1e-9)/bar)})
    covered=not g.get('validity') or g['validity'][0]<=start and end<=g['validity'][1]
    return {'status':'confirmed_grid_observations' if g['confirmed'] and covered else 'provisional_preview','events':rows,'warning':'Offsets describe pitched onsets relative to this grid, not intentional groove or syllable attacks.'}

class MusicalContext:
    def __init__(self,root):self.root=root/'musical-context'
    def directory(self,source,kind):
        if not re.fullmatch('[a-f0-9]{64}',source) or kind not in ('sections','grid'):raise ValueError('Invalid context identity')
        return self.root/source/kind
    def get(self,source,kind):
        path=self.directory(source,kind)/'current.json'
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'revision':None,'source_hash':source,'value':[] if kind=='sections' else None}
    def save(self,source,kind,value,base,duration):
        current=self.get(source,kind)
        if current['revision']!=base:raise ValueError('Musical context changed; reload before saving')
        if kind=='grid':
            value=validate_grid(value)
            validity=value.get('validity',[0,duration])
            if len(validity)!=2 or not all(math.isfinite(v) for v in validity) or not 0<=validity[0]<validity[1]<=duration:raise ValueError('Invalid grid validity interval')
            value['validity']=validity
        else:
            value=sorted(value,key=lambda s:s['start']);ids=set()
            for i,s in enumerate(value):
                if s['id'] in ids or s['type'] not in TYPES or not all(math.isfinite(s[k]) for k in ('start','end')) or not 0<=s['start']<s['end']<=duration:raise ValueError('Invalid section boundaries, type or identity')
                if i and value[i-1]['end']>s['start']+1e-9:raise ValueError('Sections cannot overlap')
                ids.add(s['id']);s['name']=str(s['name'])[:160]
        revision=uuid4().hex
        row={'format':'melolysis-musical-context-v1','author':'local user','source_hash':source,'revision':revision,'parent_revision':base,'value':value,'updated':datetime.now(timezone.utc).isoformat()}
        directory=self.directory(source,kind);write_json(directory/'revisions'/(revision+'.json'),row);write_json(directory/'current.json',row)
        return row
