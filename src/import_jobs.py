"""Durable upload-processing status; inference never holds the workspace UI lock."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from threading import RLock, Thread
from uuid import uuid4

from .storage import key_for, write_json


class ImportJobs:
    def __init__(self, root, analyze):
        self.directory = root / 'import-jobs'
        self.analyze = analyze
        self.lock = RLock()
        self.jobs = {}
        self.running = False
        for path in self.directory.glob('*.json'):
            job = json.loads(path.read_text(encoding='utf-8'))
            if job['status'] in {'queued', 'processing'}:
                job.update(status='interrupted', error='Server stopped during processing. The uploaded file is safe; click Retry.')
                write_json(path, job)
            self.jobs[job['id']] = job

    def list(self):
        with self.lock:
            return deepcopy(sorted(self.jobs.values(), key=lambda j: j['created'], reverse=True))

    def submit(self, request):
        identity = key_for(request)
        with self.lock:
            for job in self.jobs.values():
                if job['identity'] == identity and job['status'] in {'queued', 'processing', 'complete'}:
                    return deepcopy(job)
            job = dict(id=uuid4().hex, identity=identity, request=deepcopy(request),
                       name=request.get('metadata', {}).get('song', 'Imported audio'),
                       created=datetime.now(timezone.utc).isoformat(), status='queued')
            self.jobs[job['id']] = job
            self.save(job)
            if not self.running:
                self.running = True
                Thread(target=self.work, daemon=True, name='melolysis-imports').start()
            return deepcopy(job)

    def save(self, job):
        write_json(self.directory / (job['id'] + '.json'), job)

    def work(self):
        while True:
            with self.lock:
                job = next((j for j in self.jobs.values() if j['status'] == 'queued'), None)
                if job is None:
                    self.running = False
                    return
                job['status'] = 'processing'
                self.save(job)
            try:
                result = self.analyze(deepcopy(job['request']))
                update = dict(status='complete', analysis_id=result['id'])
            except Exception as exc:
                update = dict(status='failed', error=str(exc))
            with self.lock:
                job.update(update)
                self.save(job)
