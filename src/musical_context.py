"""Independent musical context revisions; never modifies note editions."""
import json, math, re
from uuid import uuid4
from datetime import datetime, timezone
from .storage import write_json, key_for

TYPES={'verse','pre-chorus','chorus','post-chorus','bridge','intro','outro','instrumental','custom'}
SECTION_EPSILON=1e-6

def section_projection(sections, layer='structure'):
    """Legacy records are structural. Never infer classification from a name."""
    if layer not in ('structure','analysis','all'):raise ValueError('Unknown section layer')
    return sorted((s for s in sections if layer=='all' or s.get('layer','structure')==layer),
                  key=lambda s:(s['start'],s['end'],s['id']))

def section_range_summary(rows):
    """Overlap components contribute once; source/work support stays independent."""
    sources={}
    for row in rows:sources.setdefault((row['work_id'] or row['source_hash'],row['source_hash']),[]).append(row)
    works={}
    for (work,source),rs in sources.items():
        components=[]
        for row in sorted(rs,key=lambda r:(r['section']['start'],r['section']['end'],r['section']['id'])):
            start,end=row['section']['start'],row['section']['end']
            if components and start<components[-1][0]-SECTION_EPSILON:
                components[-1][0]=max(end,components[-1][0]);components[-1][1].update({n['id']:n for n in row['notes']})
            else:components.append([end,{n['id']:n for n in row['notes']}])
        ranges=[max(n['pitch'] for n in ns.values())-min(n['pitch'] for n in ns.values()) for _,ns in components if ns]
        if ranges:works.setdefault(work,[]).append(sum(ranges)/len(ranges))
    return sum(sum(v)/len(v) for v in works.values())/len(works) if works else None

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
            value=json.loads(json.dumps(value));value=sorted(value,key=lambda s:(s['start'],s['end'],s['id']));ids=set();structural=[]
            for i,s in enumerate(value):
                if s['id'] in ids or s['type'] not in TYPES or not all(math.isfinite(s[k]) for k in ('start','end')) or not 0<=s['start']<s['end']<=duration:raise ValueError('Invalid section boundaries, type or identity')
                layer=s.get('layer','structure')
                if layer not in ('structure','analysis'):raise ValueError('Unknown section layer')
                if layer=='analysis' and s.get('overlap_policy')!='allow':raise ValueError('Analytical annotations require explicit overlap_policy=allow')
                if layer=='structure':
                    if any(o['end']>s['start']+SECTION_EPSILON for o in structural):raise ValueError('Structural sections overlap: adjust a shared boundary or explicitly keep an analytical annotation')
                    structural.append(s)
                if s.get('name_mode','custom') not in ('auto','custom'):raise ValueError('Invalid section name mode')
                ids.add(s['id']);s['name']=str(s.get('name') or s['type'].capitalize()+' '+str(sum(o['type']==s['type'] for o in value[:i])+1))[:160]
        revision=uuid4().hex
        row={'format':'melolysis-musical-context-v2' if kind=='sections' else 'melolysis-musical-context-v1','author':'local user','source_hash':source,'revision':revision,'parent_revision':base,'value':value,'updated':datetime.now(timezone.utc).isoformat()}
        directory=self.directory(source,kind);write_json(directory/'revisions'/(revision+'.json'),row);write_json(directory/'current.json',row)
        return row
