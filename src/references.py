"""Independent, versioned source-time human references, never prediction/correction files."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from uuid import uuid4
from .schema import NoteEvent, PitchTrack, notes_from_dicts
from .storage import content_hash, write_json

PROTOCOL_VERSION = 'singing-notes-v1'
SPLITS = {'unassigned','development','heldout'}
REGION_KINDS = {'uncertain','vibrato','glissando','grace_note','repeated_pitch','melisma','breath','leakage'}


def now():
    return datetime.now(timezone.utc).isoformat()


def reference_notes(value):
    """Published labels may contain authored overlaps; preserve them, never fix silently."""
    if value.get('origin',{}).get('kind') != 'published_human_dataset':
        return notes_from_dicts(value['notes'])
    fields = NoteEvent.__dataclass_fields__
    notes = [NoteEvent(**{k:v for k,v in row.items() if k in fields}) for row in value['notes']]
    if len({n.id for n in notes}) != len(notes):
        raise ValueError('Duplicate reference note IDs')
    return sorted(notes,key=lambda n:(n.start,n.end))


def validate_reference(value, require_review=False):
    a,b = value['excerpt']['start'],value['excerpt']['end']
    if not all(math.isfinite(t) for t in (a,b)) or not 0 <= a < b <= value['audio']['duration']+1e-6:
        raise ValueError('Reference excerpt is outside the original source timeline')
    if value['split'] not in SPLITS or not value.get('song_group'):
        raise ValueError('Reference requires a valid split and song/singer group')
    notes = reference_notes(value)
    if any(n.start < a-1e-6 or n.end > b+1e-6 for n in notes):
        raise ValueError('Reference notes must lie inside the selected source excerpt')
    if not value.get('annotator','').strip():
        raise ValueError('An annotator name or published annotation identity is required')
    if value.get('protocol') != PROTOCOL_VERSION and not value.get('origin',{}).get('convention'):
        raise ValueError('Record the annotation convention')
    for region in value.get('regions',[]):
        if region.get('kind') not in REGION_KINDS:
            raise ValueError('Unknown reference region label')
        start,end=region['start'],region['end']
        if not all(math.isfinite(t) for t in (start,end)) or not a <= start < end <= b:
            raise ValueError('Region must lie within the source excerpt')
        if region['kind']=='uncertain' and not region.get('reason','').strip():
            raise ValueError('An uncertain region needs a reason')
    if value.get('pitch'):
        PitchTrack(**value['pitch'])
    review=value.get('review',{})
    if require_review and (review.get('status')!='reviewed' or not review.get('reviewer','').strip()):
        raise ValueError('Draft annotation cannot be scored as a human-reviewed reference')
    return value


class ReferenceStore:
    def __init__(self, root):
        self.root=Path(root)

    def path(self, identifier):
        if not re.fullmatch(r'[a-f0-9]{32}',identifier):
            raise ValueError('Invalid reference identifier')
        return self.root/identifier

    def list(self, source_hash=None):
        values=[]
        for folder in sorted(self.root.glob('*')):
            if folder.is_dir() and re.fullmatch(r'[a-f0-9]{32}',folder.name):
                value=self.load(folder.name)
                if source_hash is None or value['audio']['content_sha256']==source_hash:
                    values.append(value)
        return values

    def load(self, identifier, revision=None):
        folder=self.path(identifier)
        if revision:
            if not re.fullmatch(r'[a-f0-9]{32}',revision):
                raise ValueError('Invalid revision identifier')
            path=folder/(revision+'.json')
        else:
            pointer=json.loads((folder/'latest.json').read_text(encoding='utf-8'))
            return self.load(identifier,pointer['revision'])
        value=json.loads(path.read_text(encoding='utf-8'))
        if value['id']!=identifier or value['revision']!=path.stem:
            raise ValueError('Reference identity mismatch')
        return validate_reference(value)

    def history(self, identifier):
        return sorted([self.load(identifier,p.stem) for p in self.path(identifier).glob('*.json')
            if p.stem!='latest'],key=lambda r:r.get('saved_at',r.get('created_at','')),reverse=True)

    def restore(self, identifier, revision, base_revision):
        current=self.load(identifier);old=self.load(identifier,revision)
        # Reinstating old labels never reinstates a listening attestation or split.
        return self.save(identifier,old['notes'],old.get('regions',[]),current['annotator'],
            base_revision=base_revision,restored_from_revision=revision)

    def check_split(self, value):
        if value['split']=='unassigned':
            return
        for other in self.list():
            same_source=other['audio']['content_sha256']==value['audio']['content_sha256']
            same_group=other['song_group']==value['song_group']
            if (same_source or same_group) and other['split'] not in {'unassigned',value['split']}:
                raise ValueError('Leakage: one source/song/singer group cannot span development and heldout')

    def _append(self, value):
        validate_reference(value)
        self.check_split(value)
        value={**value,'revision':uuid4().hex,'saved_at':now()}
        folder=self.path(value['id'])
        write_json(folder/(value['revision']+'.json'),value)
        write_json(folder/'latest.json',{'revision':value['revision']})
        return value

    def create(self, report, start, end, annotator, split='unassigned', song_group=None, seed=False):
        audio=report['audio']
        sr=audio['original_sample_rate']
        start_sample,end_sample=round(float(start)*sr),round(float(end)*sr)
        start,end=start_sample/sr,end_sample/sr
        rows=[];regions=[]
        if seed:
            for n in notes_from_dicts(report['predicted_notes']):
                if n.end<=start or n.start>=end:
                    continue
                a,b=max(start,n.start),min(end,n.end)
                rows.append(replace(n,start=a,end=b,frame_start=0,frame_end=0,
                                    flags=[*n.flags,'unreviewed_model_seed']).to_dict())
                if n.start<start or n.end>end:
                    regions.append({'kind':'uncertain','start':a,'end':b,
                        'reason':'Note crosses excerpt boundary; move the excerpt to a rest or exclude this event'})
        value={'format':'melolysis-human-reference-v1','id':uuid4().hex,'created_at':now(),
            'audio':dict(audio),'excerpt':{'start':start,'end':end,'start_sample':start_sample,
                'end_sample':end_sample,'sample_rate':sr},'notes':rows,'regions':regions,
            'annotator':annotator,'protocol':PROTOCOL_VERSION,'split':split,
            'song_group':song_group or audio['content_sha256'],
            'origin':{'kind':'model_assisted_draft' if seed else 'manual_from_scratch',
                'seed_prediction_id':report['prediction_id'] if seed else None,
                'independent_of_melolysis':not seed},
            'review':{'status':'draft','reviewer':'','attestation':False},'pitch':None,
            'metadata':dict(report.get('metadata',{}))}
        return self._append(value)

    def save(self, identifier, notes, regions, annotator, reviewer='', reviewed=False, attestation=False,
             base_revision=None,split=None,song_group=None,restored_from_revision=None):
        previous=self.load(identifier)
        if base_revision is not None and previous['revision']!=base_revision:
            raise ValueError('Reference changed since it was loaded; reload before saving')
        if previous['origin']['kind']=='published_human_dataset':
            raise ValueError('Published references are immutable; create a manual reference to propose another edition')
        if reviewed and (not attestation or not reviewer.strip()):
            raise ValueError('Reviewed status requires explicit human listening/boundary-review attestation and reviewer name')
        if split is not None and previous['split']!='unassigned' and split!=previous['split']:
            raise ValueError('An assigned evaluation split cannot change; reserve fresh sources for heldout evaluation')
        value={**previous,'notes':[n.to_dict() for n in notes_from_dicts(notes)],'regions':regions,
            'annotator':annotator,'parent_revision':previous['revision'],
            'split':previous['split'] if split is None else split,
            'song_group':previous['song_group'] if song_group is None else song_group,
            'review':{'status':'reviewed' if reviewed else 'draft','reviewer':reviewer.strip(),
                      'attestation':bool(attestation),'reviewed_at':now() if reviewed else None,
                      'second_person_review':bool(reviewed and reviewer.strip()!=annotator.strip())}}
        value.pop('restored_from_revision',None)
        if restored_from_revision:
            value['restored_from_revision']=restored_from_revision
        return self._append(value)

    def import_published(self, value):
        if value['origin']['kind']!='published_human_dataset' or not all(
            value['origin'].get(k) for k in ('citation','license','annotation_sha256','convention')):
            raise ValueError('Published references need citation, license, annotation checksum and convention')
        validate_reference(value,require_review=True)
        # A stable origin key makes re-import idempotent without replacing user work.
        for other in self.list():
            if other.get('origin',{}).get('annotation_sha256')==value['origin']['annotation_sha256'] and other['audio']['content_sha256']==value['audio']['content_sha256']:
                return other
        return self._append({**value,'id':uuid4().hex,'created_at':now()})

    def export_manifest(self, path, identifiers=None):
        path=Path(path).resolve()
        values=[self.load(i) for i in identifiers] if identifiers is not None else self.list()
        items=[]
        for value in values:
            validate_reference(value,require_review=True)
            if value['split']=='unassigned':
                raise ValueError('Assign a development or heldout split before freezing a reference')
            artifact=(self.path(value['id'])/(value['revision']+'.json')).resolve()
            items.append({'audio':value['audio']['source_path'],'reference':str(artifact),
                'source_sha256':value['audio']['content_sha256'],'reference_sha256':content_hash(artifact),
                'reference_id':value['id'],'revision':value['revision'],'split':value['split'],
                'song_group':value['song_group'],'annotator':value['annotator'],
                'convention':value.get('origin',{}).get('convention',value['protocol'])})
        manifest={'format':'melolysis-real-evaluation-v1','created_at':now(),'items':items,
            'policy':'Exact reference revisions/checksums; no draft scoring; grouped splits; no automatic offset fitting'}
        write_json(path,manifest)
        return manifest
