"""Local-only review application using the existing Python pipeline, no cloud service."""
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from urllib.parse import parse_qs, urlparse
import hashlib
import json
import logging
import mimetypes
import re
import traceback
from .audio_processor import SUPPORTED_AUDIO_EXTENSIONS
from .composition import CompositionConfig, generate_candidates
from .corpus import assess_attempt, profile_artist, songwriting_exercises
from .features import analyze_notes
from .motifs import discover_motifs
from .note_models import attach_frames
from .pipeline import analyze_file, export_notes, load_report
from .schema import AnalysisConfig, PitchTrack, notes_from_dicts
from .storage import key_for, latest_correction, correction_history, save_correction, write_json,content_hash
from .transcription import assign_phrases
from .references import ReferenceStore
from .real_metrics import score_reference
from .library import recording_groups,validate_corpus_sources
from .learning_store import LearningStore,ACTIONS as LEARNING_ACTIONS
from .import_jobs import ImportJobs
from .musical_context import MusicalContext, rhythm

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "web"


class Workspace:
    def __init__(self, root="outputs"):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.musical_context = MusicalContext(self.root)
        self.references = ReferenceStore(self.root/'references')
        self.import_jobs = ImportJobs(self.root, self.analyze_upload)

    def validate_upload(self, data):
        source_id = data['upload_id']
        if not re.fullmatch(r'[a-f0-9]{64}\.(wav|mp3|flac|m4a|ogg|aac)', source_id):
            raise ValueError('Invalid upload identifier')
        if not (self.root/'imports'/source_id).is_file():
            raise ValueError('Uploaded file not found; upload it again')
        AnalysisConfig(**data.get('config', {}))

    def analyze_upload(self, data):
        self.validate_upload(data)
        r = analyze_file(self.root/'imports'/data['upload_id'], self.root,
            AnalysisConfig(**data.get('config', {})), metadata=data.get('metadata'))
        return {'id': key_for(str(Path(r['report_path']).relative_to(self.root))), 'report': r}

    def catalog(self):
        paths=list((self.root/'analyses').glob('*/*/report.json'))
        paths+=list((self.root/'real-validation'/'models').glob('*/analyses/*/*/report.json'))
        return {key_for(str(p.relative_to(self.root))):p for p in sorted(paths)}

    def get_report(self, report_id):
        with self.lock:
            return self._get_report(report_id)

    def _get_report(self, report_id):
        path = self.catalog().get(report_id)
        if path is None:
            raise ValueError("Unknown analysis")
        report = load_report(path)
        correction = latest_correction(self.root/"corrections", report["audio"]["content_sha256"])
        if correction and correction["revision"] != report["provenance"].get("correction_revision"):
            self.update_active(path, report, correction)
        return path, report

    def update_active(self, path, report, correction):
        notes = assign_phrases(attach_frames(notes_from_dicts(correction["notes"]), PitchTrack(**report["raw_pitch"])),
            report["provenance"]["config"]["phrase_rest_seconds"])
        if any(n.end > report["audio"]["duration"]+.001 for n in notes):
            raise ValueError("Corrected notes exceed source duration")
        report["notes"] = [n.to_dict() for n in notes]
        report["features"] = analyze_notes(notes, PitchTrack(**report["raw_pitch"]),
            report.get("context", {}).get("beat_grid"), report.get("context", {}).get("chords"),
            report.get("context", {}).get("tonal_context"))
        report["motifs"] = discover_motifs(notes)
        report["provenance"]["correction_revision"] = correction["revision"]
        report["provenance"]["correction_base_prediction"] = correction["base_prediction"]
        export_notes(notes, path.parent/"notes.csv", path.parent/"notes.mid")
        write_json(path, report)

    def dispatch(self, action, data):
        if action == 'identity-compare':
            from .melodic_identity import compare
            # Only snapshot under the workspace lock; pair alignment must not block
            # import status, playback requests or correction saves.
            with self.lock:
                sides=[]
                for identifier in (data['a'],data['b']):
                    _,r=self.get_report(identifier)
                    validate_corpus_sources([r],self.references.list(),False,
                        [json.loads(p.read_text(encoding='utf-8')) for p in self.catalog().values()])
                    source=r['audio']['content_sha256']
                    sides.append(json.loads(json.dumps({'analysis_id':identifier,'source_hash':source,
                        'song':r['metadata'].get('song') or source,'artist':r['metadata'].get('artist',''),
                        'prediction_id':r['prediction_id'],'correction_revision':r['provenance'].get('correction_revision'),
                        'note_fingerprint':key_for(r['notes']),'notes':r['notes'],
                        'sections':self.musical_context.get(source,'sections'),'grid':self.musical_context.get(source,'grid')})))
            result=compare(*sides)
            write_json(self.root/'melodic-identity'/'runs'/(result['id']+'.json'),result)
            return result
        if action == 'identity-study':
            from .learning import passage_study, evidence
            identifier=data['run_id']
            if not re.fullmatch('[a-f0-9]{64}',identifier):raise ValueError('Invalid identity run')
            run=json.loads((self.root/'melodic-identity'/'runs'/(identifier+'.json')).read_text(encoding='utf-8'))
            m=next(m for m in run['matches'] if m['id']==data['match_id'])
            saved=self.root/'learning'/'studies'/(key_for([identifier,m['id'],'study'])+'.json')
            if saved.exists():return json.loads(saved.read_text(encoding='utf-8'))
            side=run['sources'][0];_,report=self.get_report(side['analysis_id'])
            report=json.loads(json.dumps(report));report['notes']=side['notes']
            report['metadata']={'song':side['song'],'artist':side['artist']};report['context']={}
            report['prediction_id']=side['prediction_id'];report['provenance']['correction_revision']=side['correction_revision']
            study=passage_study(report,m['a']['start'],m['a']['end'])
            finding={'id':key_for([identifier,m['id'],'learn']),'kind':'motif','title':'Develop a related gesture with your own notes',
                'text':f"{m['matched_targets']} aligned targets link these recordings: "+', '.join(m['transformations'])+'.',
                'category':'statistical_interpretation','conditions':'Local candidate; not an artist-specific signature.',
                'evidence':evidence(notes_from_dicts(m['a']['notes'])),
                'technique':{'type':'motif','title':'Invent a motif and vary its rhythm or ending',
                'instruction':'Draw your own short motif, then a related answer. Change rhythm or the ending. Listen to both sources as structural examples; choose your own pitches.',
                'constraint':{'own_motif_then_variation':True}}}
            study['findings']=[finding];study['analysis_id']=side['analysis_id']
            study['identity_evidence']={'run_id':identifier,'match_id':m['id'],'a':m['a'],'b':m['b']}
            study['id']=key_for([identifier,m['id'],'study'])
            write_json(self.root/'learning'/'studies'/(study['id']+'.json'),study)
            return study
        if action == 'import-start':
            self.validate_upload(data)
            return self.import_jobs.submit(data)
        with self.lock:
            if action in {'context-get','context-save'}:
                _,r=self.get_report(data['id']);source=r['audio']['content_sha256']
                if action=='context-save':
                    return self.musical_context.save(source,data['kind'],data['value'],data.get('base_revision'),r['audio']['duration'])
                return {kind:self.musical_context.get(source,kind) for kind in ('sections','grid')}
            if action=='section-compare':
                reports=[self.get_report(i)[1] for i in data['ids']]
                reports,scope=validate_corpus_sources(reports,self.references.list(),False)
                artists={r['metadata'].get('artist','').strip() for r in reports}
                if len(artists)!=1 or not next(iter(artists),'') or next(iter(artists))=='Unspecified singer':raise ValueError('Assign the same explicit artist to the selected songs first')
                rows=[]
                for r in reports:
                    source=r['audio']['content_sha256'];sections=self.musical_context.get(source,'sections');grid=self.musical_context.get(source,'grid')
                    for section in sections['value']:
                        if section['type']!=data['type']:continue
                        ns=[n for n in r['notes'] if section['start']<=n['start']<section['end']]
                        rows.append({'source_hash':source,'analysis_id':next(i for i in data['ids'] if self.get_report(i)[1]['audio']['content_sha256']==source),'song':r['metadata'].get('song',source),'section':section,'section_revision':sections['revision'],'grid_revision':grid['revision'],'grid':grid['value'],'notes':ns,'rhythm':rhythm(ns,grid['value'],section['start'],section['end'])})
                songs={row['song'] for row in rows}
                per_song={}
                for row in rows:
                    ns=row['notes'];row['pitch_range']=max((n['pitch'] for n in ns),default=0)-min((n['pitch'] for n in ns),default=0)
                    per_song.setdefault(row['song'],[]).append(row['pitch_range'])
                mean_range=sum(sum(v)/len(v) for v in per_song.values())/len(per_song) if per_song else None
                return {'occurrences':rows,'support_songs':len(songs),'equal_song_mean_range':mean_range,'scope':scope,'warning':'Exploratory section comparison; two songs do not establish an artist signature.'}
            if action in LEARNING_ACTIONS:
                return LearningStore(self).dispatch(action,data)
            if action=='reference-create':
                _,report=self.get_report(data['id'])
                return self.references.create(report,data['start'],data['end'],data['annotator'],
                    data.get('split','unassigned'),data.get('song_group'),bool(data.get('seed',False)))
            if action=='reference-save':
                return self.references.save(data['reference_id'],data['notes'],data.get('regions',[]),
                    data['annotator'],data.get('reviewer',''),bool(data.get('reviewed',False)),
                    bool(data.get('attestation',False)),data.get('base_revision'),data.get('split'),data.get('song_group'))
            if action=='reference-restore':
                return self.references.restore(data['reference_id'],data['revision'],data['base_revision'])
            if action=='restore-correction':
                path,r=self.get_report(data['id'])
                if 'base_revision' in data and data['base_revision']!=r['provenance'].get('correction_revision'):
                    raise ValueError('Working correction changed since loading; reload before restoring')
                revisions=correction_history(self.root/'corrections',r['audio']['content_sha256'])
                old=next((v for v in revisions if v['revision']==data['revision']),None)
                if old is None: raise ValueError('Unknown correction revision for this source')
                c=save_correction(self.root/'corrections',r['audio']['content_sha256'],old['notes'],r['prediction_id'])
                self.update_active(path,r,c);return r
            if action=='reference-score':
                _,report=self.get_report(data['id'])
                ref=self.references.load(data['reference_id'])
                score=score_reference(ref,report,require_review=ref['review']['status']=='reviewed')
                score['validation_status']='reviewed_reference_comparison' if ref['review']['status']=='reviewed' else 'DRAFT PREVIEW ONLY — not validated accuracy'
                return score
            if action=='reference-manifest':
                ids=[r['id'] for r in self.references.list() if r['review']['status']=='reviewed' and r['split']!='unassigned']
                if not ids:
                    raise ValueError('No reviewed, split-assigned human references are ready for evaluation')
                return self.references.export_manifest(self.root/'real-validation'/'reviewed.manifest.json',ids)
            if action == "analyze":
                return self.analyze_upload(data)
            if action == "correct":
                path, r = self.get_report(data["id"])
                current=latest_correction(self.root/'corrections',r['audio']['content_sha256'])
                if 'base_revision' in data and data['base_revision']!=(current['revision'] if current else None):
                    raise ValueError('Working correction changed since loading; reload before saving')
                notes = notes_from_dicts(data["notes"])
                if any(n.end > r["audio"]["duration"]+.001 for n in notes):
                    raise ValueError("Notes exceed source duration")
                c = save_correction(self.root/"corrections", r["audio"]["content_sha256"], notes, r["prediction_id"])
                self.update_active(path, r, c)
                return r
            if action == "metadata":
                path, r = self.get_report(data["id"])
                allowed = {"artist", "song", "section", "tempo", "key", "mode", "language", "genre", "tags"}
                r["metadata"].update({k: v for k, v in data["metadata"].items() if k in allowed})
                write_json(path, r)
                return r
            if action in {"profile", "compose", "exercises"}:
                reports = [self.get_report(i)[1] for i in data["ids"]]
                reference = [self.get_report(i)[1] for i in data.get("reference_ids", [])]
                source_context=[json.loads(p.read_text(encoding='utf-8')) for p in self.catalog().values()]
                refs=self.references.list()
                reports,scope=validate_corpus_sources(reports,refs,data.get('allow_research',False),source_context)
                reference,reference_scope=validate_corpus_sources(reference,refs,data.get('allow_research',False),source_context)
                profile = profile_artist(reports, data.get("artist", "Selected recordings"), reference)
                profile['corpus_scope']=scope
                if scope['research_opt_in'] or reference_scope['research_opt_in']:
                    profile['warnings'].append('Explicit research corpus: includes dataset recordings; do not interpret this as a single artist-specific corpus.')
                exercises = songwriting_exercises(profile)
                profile["exercises"] = exercises
                if action != "compose":
                    write_json(self.root/"profiles"/(key_for(profile)+".json"), profile)
                    return profile
                c = CompositionConfig(**data.get("config", {}))
                result = generate_candidates(profile, c)
                identifier = key_for(result)
                directory = self.root/"compositions"/identifier
                write_json(directory/"candidates.json", result)
                for i, candidate in enumerate(result["candidates"]):
                    export_notes(notes_from_dicts(candidate["notes"]), directory/f"candidate-{i}.csv",
                                 directory/f"candidate-{i}.mid", c.tempo)
                result["id"] = identifier
                return result
            if action == "attempt":
                _, report = self.get_report(data["id"])
                return assess_attempt(notes_from_dicts(report["notes"]), data["exercise"])
            raise ValueError("Unknown action")


def make_handler(workspace):
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, mime="application/json", extra=None):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, allow_nan=False).encode()
            if isinstance(body, str):
                body = body.encode()
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def do_GET(self):
            if not self.allowed_host():
                return self.send(403, {"error": "Local workspace only"})
            try:
                parsed = urlparse(self.path)
                query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                if parsed.path == '/api/import-jobs':
                    return self.send(200, workspace.import_jobs.list())
                if parsed.path == "/api/state":
                    rows = []
                    for identifier in workspace.catalog():
                        _, r = workspace.get_report(identifier)
                        rows.append({"id": identifier, "metadata": r["metadata"], "audio": r["audio"],
                            "model": r["provenance"]["note_model"], "notes": len(r["notes"]),
                            'estimator':r['raw_pitch']['model'],'prediction_id':r['prediction_id'],
                            "correction_revision": r["provenance"].get("correction_revision")})
                    refs=workspace.references.list()
                    return self.send(200, {"analyses": rows,'recordings':recording_groups(rows,refs),
                        'selection_policy':'Unique source hashes; no automatic inclusion; research datasets require explicit corpus opt-in'})
                if parsed.path == "/api/report":
                    return self.send(200, workspace.get_report(query["id"])[1])
                if parsed.path=='/api/idea-export':
                    return self.send_file(LearningStore(workspace).export(query['id'],query['revision'],query.get('type','midi')),attachment=True)
                if parsed.path=='/api/references':
                    _,report=workspace.get_report(query['id'])
                    refs=workspace.references.list(report['audio']['content_sha256'])
                    return self.send(200,[{k:r[k] for k in ('id','revision','excerpt','review','annotator','origin','split')} for r in refs])
                if parsed.path=='/api/reference':
                    return self.send(200,workspace.references.load(query['reference_id'],query.get('revision')))
                if parsed.path=='/api/reference-history':
                    return self.send(200,workspace.references.history(query['reference_id']))
                if parsed.path=='/api/correction-history':
                    _,report=workspace.get_report(query['id'])
                    return self.send(200,correction_history(workspace.root/'corrections',report['audio']['content_sha256']))
                if parsed.path=='/api/source-audio':
                    _,report=workspace.get_report(query['id']);source=Path(report['audio']['source_path'])
                    if content_hash(source)!=report['audio']['content_sha256']:
                        raise ValueError('Original audio changed since analysis; reanalyze before annotation')
                    return self.send_file(source)
                if parsed.path=='/api/annotation-protocol':
                    return self.send(200,(STATIC.parent.parent/'docs'/'ANNOTATION_PROTOCOL.md').read_text(encoding='utf-8'),'text/plain; charset=utf-8')
                if parsed.path in {"/api/audio", "/api/download"}:
                    path, _ = workspace.get_report(query["id"])
                    kind = query.get("type", "json")
                    names = {"json": "report.json", "csv": "notes.csv", "midi": "notes.mid"}
                    name = "playback.wav" if parsed.path == "/api/audio" else names[kind]
                    return self.send_file(path.parent/name, attachment=parsed.path == "/api/download")
                if parsed.path == "/api/candidate":
                    identifier = query["id"]
                    index = int(query["index"])
                    if not re.fullmatch(r"[a-f0-9]{64}", identifier) or not 0 <= index < 8:
                        raise ValueError("Invalid candidate")
                    return self.send_file(workspace.root/"compositions"/identifier/f"candidate-{index}.mid", attachment=True)
                files = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css",
                    '/editor-core.js':'editor-core.js','/editor.js':'editor.js','/audition.js':'audition.js','/library.js':'library.js',
                    '/learning.js':'learning.js','/learning-roll.js':'learning-roll.js','/learning.css':'learning.css',
                    '/imports.js':'imports.js','/context.js':'context.js','/artist-identity.js':'artist-identity.js'}
                if parsed.path in files:
                    path = STATIC/files[parsed.path]
                    return self.send(200, path.read_bytes(), mimetypes.guess_type(path)[0] or "text/plain")
                self.send(404, {"error": "Not found"})
            except (ValueError, KeyError, FileNotFoundError) as exc:
                self.send(400, {"error": str(exc)})

        def send_file(self, path, attachment=False):
            size = path.stat().st_size
            start, end, status = 0, size-1, 200
            range_header = self.headers.get("Range")
            if range_header:
                match = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
                if not match:
                    return self.send(416, "Invalid range")
                start = int(match[1]); end = min(size-1, int(match[2]) if match[2] else size-1)
                if start > end:
                    return self.send(416, "Invalid range")
                status = 206
            extra = {"Accept-Ranges": "bytes"}
            if status == 206:
                extra["Content-Range"] = f"bytes {start}-{end}/{size}"
            if attachment:
                extra["Content-Disposition"] = f'attachment; filename="{path.name}"'
            with path.open("rb") as f:
                f.seek(start)
                self.send(status, f.read(end-start+1), mimetypes.guess_type(path)[0] or "application/octet-stream", extra)

        def do_POST(self):
            if not self.allowed_host() or self.headers.get("Origin") not in {
                f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                return self.send(403, {"error": "Same-origin local requests required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 256*1024*1024:
                    return self.send(413, {"error": "Upload limit is 256 MiB per recording"})
                body = self.rfile.read(length)
                parsed = urlparse(self.path)
                if parsed.path == "/api/import":
                    name = parse_qs(parsed.query).get("name", [""])[0]
                    suffix = Path(name).suffix.lower()
                    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
                        raise ValueError("Upload WAV, FLAC, MP3, M4A, OGG or AAC")
                    identifier = hashlib.sha256(body).hexdigest()+suffix
                    directory = workspace.root/"imports"
                    directory.mkdir(parents=True, exist_ok=True)
                    path = directory/identifier
                    if not path.exists():
                        path.write_bytes(body)
                    return self.send(200, {"upload_id": identifier, "original_name": Path(name).name})
                if not parsed.path.startswith("/api/"):
                    raise ValueError("Unknown action")
                return self.send(200, workspace.dispatch(parsed.path.removeprefix("/api/"), json.loads(body)))
            except Exception as exc:
                log.error("Workspace request failed: %s", exc)
                self.send(400, {"error": str(exc)})

        def log_message(self, fmt, *args):
            log.info(fmt, *args)
    return Handler


def serve(root="outputs", port=8765):
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Workspace(root)))
    print(f"Melolysis workspace: http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
