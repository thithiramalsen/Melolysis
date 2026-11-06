"""Non-destructive identity reconciliation and immutable input snapshots.

Reading or previewing a migration writes nothing. Legacy metadata is suggestion
text only. All authoritative changes live in this independent sidecar store.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4
from .identity_schema import FORMAT, recording_id, label
from .library import recording_groups, validate_corpus_sources
from .storage import key_for, write_json, content_hash


class IdentityCatalog:
    def __init__(self, workspace):
        self.workspace = workspace
        self.root = workspace.root / 'melodic-intelligence'

    def current(self):
        path = self.root / 'catalog/current.json'
        if not path.exists():
            return dict(format=FORMAT, schema_version=1, revision=None,
                        artists={}, works={}, associations={})
        row = json.loads(path.read_text(encoding='utf-8'))
        if row.get('format') != FORMAT or row.get('schema_version') != 1:
            raise ValueError('Unsupported catalog format; existing catalog was not changed')
        return row

    def reports(self):
        # get_report resolves working corrections in memory, without materializing
        # them back into historical analysis reports.
        return {i: self.workspace.get_report(i)[1] for i in self.workspace.catalog()}

    def view(self, catalog=None):
        c = deepcopy(catalog if catalog is not None else self.current())
        reports = self.reports()
        rows = []
        for identifier, r in reports.items():
            rows.append(dict(id=identifier, metadata=r['metadata'], audio=r['audio'],
                model=r['provenance']['note_model'], estimator=r['raw_pitch']['model'],
                prediction_id=r['prediction_id'], correction_revision=r['provenance'].get('correction_revision')))
        groups = recording_groups(rows, self.workspace.references.list())
        for g in groups:
            source = g['source_hash']; a = c['associations'].get(source, {})
            g.update(recording_id=recording_id(source), work_id=a.get('work_id'),
                artist_ids=a.get('artist_ids', []), take=a.get('take', ''),
                identity_status='confirmed' if a.get('work_id') and a.get('artist_ids') else 'unresolved',
                metadata_suggestions={'artist':g['artist'], 'song':g['name']})
            g['artist'] = ', '.join(c['artists'][i]['name'] for i in g['artist_ids'])
            g['work_title'] = c['works'][g['work_id']]['title'] if g['work_id'] else None
            g['song_key'] = ['work',g['work_id']] if g['work_id'] else ['unresolved',source]
            if a.get('preferred_analysis') in g['analysis_ids']:
                g['preferred_analysis'] = a['preferred_analysis']
            g['editions'] = [self.edition(i, reports[i]) for i in g['analysis_ids']]
            g['rights'] = {'status':'not_supplied', 'redistribution_permission':None}
        c['recordings'] = groups
        c['counts'] = self.counts(groups)
        return c

    @staticmethod
    def counts(groups):
        return dict(recordings=len(groups), works=len({g['work_id'] for g in groups if g['work_id']}),
                    unresolved_recordings=sum(g['identity_status']=='unresolved' for g in groups))

    @staticmethod
    def edition(identifier, r):
        value = dict(analysis_id=identifier, source_hash=r['audio']['content_sha256'],
            prediction_id=r['prediction_id'], correction_revision=r['provenance'].get('correction_revision'),
            note_fingerprint=key_for(r['notes']), model=r['provenance']['note_model'],
            estimator=r['raw_pitch']['model'],
            configuration=r['provenance']['config'])
        return dict(id=key_for(value), **value)

    def reconcile(self, data):
        current = self.current()
        if data.get('base_revision') != current['revision']:
            raise ValueError('Catalog changed since loading. Reload associations before saving.')
        before = self.view(current); groups = {g['source_hash']:g for g in before['recordings']}
        source = data['source_hash']
        if not isinstance(source,str) or source not in groups:
            raise ValueError('Unknown recording source')
        c = deepcopy(current)
        artist_ids = data.get('artist_ids', [])
        if not isinstance(artist_ids, list) or len(artist_ids)>20 or any(not isinstance(i,str) for i in artist_ids):
            raise ValueError('Choose artist identifiers')
        artist_ids = list(dict.fromkeys(artist_ids))
        if any(i not in c['artists'] for i in artist_ids):
            raise ValueError('Unknown artist')
        if data.get('new_artist'):
            i = uuid4().hex
            c['artists'][i] = dict(id=i, name=label(data['new_artist'],'artist name',True),
                aliases=[], external_ids={}, provenance='explicit local user association')
            artist_ids.append(i)
        work = data.get('work_id') or None
        if work and (not isinstance(work,str) or work not in c['works']):
            raise ValueError('Unknown musical work')
        if data.get('new_work'):
            work = uuid4().hex
            c['works'][work] = dict(id=work,title=label(data['new_work'],'work title',True),
                aliases=[], creators=[], provenance='explicit local user association')
        preferred = data.get('preferred_analysis') or groups[source]['preferred_analysis']
        if not isinstance(preferred,str) or preferred not in groups[source]['analysis_ids']:
            raise ValueError('Primary analysis belongs to another recording')
        c['associations'][source] = dict(recording_id=recording_id(source), source_hash=source,
            work_id=work, artist_ids=artist_ids, take=label(data.get('take',''),'take/version'),
            preferred_analysis=preferred, provenance='explicit local user association')
        after = self.view(c)
        if data.get('dry_run') is True:
            return dict(before=before['counts'], after=after['counts'], preview=after, writes=False)
        c.update(revision=uuid4().hex, parent_revision=current['revision'],
                 updated=datetime.now(timezone.utc).isoformat())
        write_json(self.root/'catalog/revisions'/(c['revision']+'.json'), c)
        write_json(self.root/'catalog/current.json', c)
        return self.view(c)

    def decorate(self, reports):
        c = self.current(); result = deepcopy(reports)
        for r in result:
            source=r['audio']['content_sha256']; a=c['associations'].get(source,{})
            r['catalog_identity'] = dict(recording_id=recording_id(source),work_id=a.get('work_id'),
                artist_ids=a.get('artist_ids',[]),catalog_revision=c['revision'])
            if a.get('work_id'):r['metadata']['song']=c['works'][a['work_id']]['title']
            r['metadata']['artist']=', '.join(c['artists'][i]['name'] for i in a.get('artist_ids',[])) or 'Unresolved artist'
        return result

    def snapshot(self, data):
        c=self.view()
        if data.get('catalog_revision') != c['revision']:
            raise ValueError('Catalog changed. Reload before pinning a snapshot.')
        reports=self.reports(); ids=data.get('ids',[])
        if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in reports for i in ids):
            raise ValueError('Choose existing analyses')
        # A caller must explicitly choose one primary edition per source.
        selected={}
        for i in dict.fromkeys(ids):
            source=reports[i]['audio']['content_sha256']
            if source in selected:raise ValueError('Choose one analysis edition per recording')
            selected[source]=i
        purpose=data.get('purpose','artist')
        if purpose not in ('artist','research'):raise ValueError('Unknown corpus purpose')
        validate_corpus_sources([reports[i] for i in selected.values()],self.workspace.references.list(),
                                purpose=='research',list(reports.values()))
        entries=[]
        for source,i in sorted(selected.items()):
            r=reports[i]; group=next(g for g in c['recordings'] if g['source_hash']==source)
            path=Path(r['audio']['source_path'])
            availability='available' if path.is_file() and content_hash(path)==source else 'missing_or_changed'
            entries.append(dict(recording_id=group['recording_id'],source_hash=source,
                work_id=group['work_id'],artist_ids=group['artist_ids'],identity_status=group['identity_status'],
                category=group['category'],edition=self.edition(i,r),notes=r['notes'],audio=r['audio'],
                rights=group['rights'],
                source_availability=availability,context={k:self.workspace.musical_context.get(source,k) for k in ('sections','grid')},
                supplied_context=r.get('context',{})))
        value=dict(format='melolysis-corpus-snapshot-v1',schema_version=1,catalog_revision=c['revision'],
            catalog={k:c[k] for k in ('artists','works','associations')},purpose=purpose,
            entries=entries,counts=self.counts([g for g in c['recordings'] if g['source_hash'] in selected]),
            timebase='original_source_seconds', policy='one explicit edition per source; equal-work aggregation',
            exclusions=[g['recording_id'] for g in c['recordings'] if g['source_hash'] not in selected])
        value['id']=key_for(value)
        if not data.get('dry_run'):
            path=self.root/'corpora'/(value['id']+'.json')
            if not path.exists():write_json(path,value)
        return value

    def load_snapshot(self, identifier):
        if not isinstance(identifier,str) or not re.fullmatch('[a-f0-9]{64}',identifier):raise ValueError('Invalid snapshot identifier')
        value=json.loads((self.root/'corpora'/(identifier+'.json')).read_text(encoding='utf-8'))
        if value.get('format')!='melolysis-corpus-snapshot-v1':raise ValueError('Unsupported snapshot format')
        if value.get('id')!=identifier or key_for({k:v for k,v in value.items() if k!='id'})!=identifier:
            raise ValueError('Snapshot integrity check failed; stored content differs from its identifier')
        return value
