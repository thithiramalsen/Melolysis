"""Local learning snapshots/bookmarks and independent, versioned composition ideas."""
from dataclasses import replace
from datetime import datetime,timezone
import json
import re
from uuid import uuid4
from .learning import passage_study,idea_config,idea_notes,assess_idea,develop_idea
from .pipeline import export_notes
from .storage import write_json
from .schema import notes_from_dicts

ACTIONS={'melody-study','melody-study-load','technique-list','technique-save','idea-list','idea-get','idea-save','idea-check','idea-develop','idea-attempt'}


class LearningStore:
    def __init__(self,workspace):self.workspace=workspace;self.root=workspace.root/'learning'

    def path(self,kind,identifier):
        if kind not in ('studies','techniques','ideas') or not re.fullmatch(r'[a-f0-9]{32}|[a-f0-9]{64}',identifier):
            raise ValueError('Invalid learning item identifier')
        return self.root/kind/identifier

    def study(self,identifier):return json.loads(self.path('studies',identifier).with_suffix('.json').read_text(encoding='utf-8'))

    def link(self,data):
        if not data.get('study_id'):return None
        study=self.study(data['study_id']);finding=next((f for f in study['findings'] if f['id']==data.get('finding_id')),None)
        if not finding or not finding['technique']:raise ValueError('Choose an evidenced technique from a saved study.')
        return {'study_id':study['id'],'analysis_id':study['analysis_id'],'source':study['source'],
            'finding':finding,'source_notes':study['notes']}

    def dispatch(self,action,data):
        if action=='melody-study-load':return self.study(data['id'])
        if action=='idea-attempt':
            from .evaluation import note_metrics
            idea=self.dispatch('idea-get',{'id':data['idea_id']});_,report=self.workspace.get_report(data['analysis_id'])
            expected=idea_notes(idea['notes'],idea['config']);performed=notes_from_dicts(report['notes'])
            if not performed:raise ValueError('The attempt has no note events. Review its transcription first.')
            factor=60/idea['config']['tempo'];origin=expected[0].start
            expected=[replace(n,start=(n.start-origin)*factor,end=(n.end-origin)*factor) for n in expected]
            origin=performed[0].start;performed=[replace(n,start=n.start-origin,end=n.end-origin) for n in performed]
            def contour(ns):return [0 if abs(b.pitch-a.pitch)<.5 else (1 if b.pitch>a.pitch else -1) for a,b in zip(ns,ns[1:])]
            ec,pc=contour(expected),contour(performed)
            return {'metrics':note_metrics(expected,performed),'contour':{'intended':ec,'performed':pc,
                'ordered_direction_agreement':sum(a==b for a,b in zip(ec,pc))/len(ec) if ec and len(ec)==len(pc) else None,
                'scope':'Ordered target directions; correspondence unavailable when note counts differ.'},
                'alignment':'First onsets aligned; fixed intended tempo; no time warping.',
                'scope':'Pitch/onset/offset agreement with your intended notes, not songwriting quality. Attempt transcription must be checked.'}
        if action=='melody-study':
            _,report=self.workspace.get_report(data['id'])
            result=passage_study(report,data['start'],data['end'],data.get('context'))
            result['analysis_id']=data['id'];path=self.path('studies',result['id']).with_suffix('.json')
            if not path.exists():write_json(path,result)
            return result
        if action=='technique-list':
            return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((self.root/'techniques').glob('*.json'))]
        if action=='technique-save':
            link=self.link(data)
            if not link:raise ValueError('Choose a source-backed technique to bookmark.')
            value={'id':link['finding']['id'],**link};path=self.path('techniques',value['id']).with_suffix('.json')
            if not path.exists():write_json(path,value)
            return value
        if action=='idea-list':
            return [{k:v[k] for k in ('id','revision','title','updated','link','config')} for p in sorted((self.root/'ideas').glob('*/current.json'))
                for v in [json.loads(p.read_text(encoding='utf-8'))]]
        if action=='idea-get':
            directory=self.path('ideas',data['id'])
            if data.get('revision'):
                self.path('ideas',data['revision']);path=directory/'revisions'/(data['revision']+'.json')
            else:path=directory/'current.json'
            return json.loads(path.read_text(encoding='utf-8'))
        if action in ('idea-save','idea-check','idea-develop'):
            config=idea_config(data.get('config',{}));notes=idea_notes(data.get('notes',[]),config);link=self.link(data)
            if action=='idea-develop':
                return [{'assessment':assess_idea(v['notes'],config,link['finding']['technique'] if link else None,link['source_notes'] if link else []),**v}
                    for v in develop_idea(data.get('notes',[]),config)]
            assessment=assess_idea(data.get('notes',[]),config,link['finding']['technique'] if link else None,link['source_notes'] if link else [])
            if action=='idea-check':return assessment
            if not notes:raise ValueError('Draw a melody before saving an idea.')
            identifier=data.get('id') or uuid4().hex;directory=self.path('ideas',identifier)
            current=json.loads((directory/'current.json').read_text(encoding='utf-8')) if (directory/'current.json').exists() else None
            if (current and data.get('base_revision')!=current['revision']) or (not current and data.get('base_revision')):
                raise ValueError('This idea changed since loading. Reload it before saving a new revision.')
            revision=uuid4().hex;value={'format':'melolysis-idea-v1','id':identifier,'revision':revision,
                'parent_revision':current['revision'] if current else None,'title':str(data.get('title','Untitled idea')).strip()[:160] or 'Untitled idea',
                'updated':datetime.now(timezone.utc).isoformat(),'config':config,'notes':[n.to_dict() for n in notes],
                'timebase':'quarter_note_beats; source timestamps remain in linked study','link':link,'assessment':assessment}
            path=directory/'revisions'/(revision+'.json');write_json(path,value)
            seconds=[replace(n,start=n.start*60/config['tempo'],end=n.end*60/config['tempo']) for n in notes]
            export_notes(seconds,midi_path=path.with_suffix('.mid'),csv_path=path.with_suffix('.csv'),tempo=config['tempo'])
            write_json(directory/'current.json',value)
            return value
        raise ValueError('Unknown learning action')

    def export(self,identifier,revision,kind):
        if kind not in ('midi','json','csv'):raise ValueError('Choose MIDI, CSV or JSON export.')
        self.path('ideas',revision)
        return self.path('ideas',identifier)/'revisions'/(revision+{'midi':'.mid','csv':'.csv','json':'.json'}[kind])
