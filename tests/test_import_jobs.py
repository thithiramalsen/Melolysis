"""Queue contracts use controlled callbacks; browser coverage also runs real inference."""
import tempfile
import time
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from src.import_jobs import ImportJobs
from src.storage import write_json
from src.workspace import Workspace


def wait_for(check):
    deadline = time.monotonic() + 5
    while not check():
        if time.monotonic() > deadline:
            raise AssertionError('Job did not settle')
        time.sleep(.01)


class ImportJobTests(unittest.TestCase):
    def test_queue_deduplicates_and_persists_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            entered, release = Event(), Event()
            calls = []
            def analyze(request):
                calls.append(request['upload_id']);entered.set();release.wait(3)
                return {'id': request['upload_id']}
            jobs = ImportJobs(Path(directory), analyze)
            request = {'upload_id': 'first', 'metadata': {'song': 'First'}}
            first = jobs.submit(request)
            self.assertTrue(entered.wait(2))
            self.assertEqual(first['id'], jobs.submit(request)['id'])
            second = jobs.submit({'upload_id': 'second'})
            self.assertEqual(jobs.jobs[second['id']]['status'], 'queued')
            release.set()
            wait_for(lambda: all(j['status'] == 'complete' for j in jobs.list()))
            self.assertEqual(calls, ['first', 'second'])
            restored = ImportJobs(Path(directory), analyze)
            self.assertEqual({j['analysis_id'] for j in restored.list()}, {'first', 'second'})
            self.assertEqual(restored.submit(request)['id'], first['id'])

    def test_failure_can_retry_without_uploading_again(self):
        with tempfile.TemporaryDirectory() as directory:
            def fail(request):
                raise ValueError('Optional model weights missing')
            jobs = ImportJobs(Path(directory), fail)
            first = jobs.submit({'upload_id': 'safe-upload'})
            wait_for(lambda: jobs.list()[0]['status'] == 'failed')
            self.assertIn('weights missing', jobs.list()[0]['error'])
            jobs.analyze = lambda request: {'id': 'recovered'}
            second = jobs.submit(first['request'])
            self.assertNotEqual(first['id'], second['id'])
            wait_for(lambda: any(j['status'] == 'complete' for j in jobs.list()))

    def test_server_restart_marks_unfinished_jobs_interrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root/'import-jobs'/'example.json',
                       dict(id='example', identity='x', request={'upload_id': 'safe'},
                            name='Unfinished', created='2026-11-05', status='processing'))
            jobs = ImportJobs(root, lambda request: {'id': 'restarted'})
            self.assertEqual(jobs.list()[0]['status'], 'interrupted')
            self.assertIn('Retry', jobs.list()[0]['error'])

    def test_async_inference_does_not_hold_workspace_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            entered, release = Event(), Event()
            def analyze(data):
                entered.set();release.wait(3);return {'id': 'result'}
            with patch.object(Workspace, 'analyze_upload', side_effect=analyze):
                workspace = Workspace(directory)
                with patch.object(workspace, 'validate_upload'):
                    workspace.dispatch('import-start', {'upload_id': 'fixture'})
                self.assertTrue(entered.wait(2))
                try:
                    self.assertTrue(workspace.lock.acquire(timeout=.2))
                    workspace.lock.release()
                    self.assertEqual(workspace.import_jobs.list()[0]['status'], 'processing')
                finally:
                    release.set()
                wait_for(lambda: workspace.import_jobs.list()[0]['status'] == 'complete')
