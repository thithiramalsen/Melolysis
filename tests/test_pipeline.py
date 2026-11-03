"""Real audio inference, native-rate decoding, exports and HTTP correction integration."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
import io
from types import SimpleNamespace
from dataclasses import replace
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import numpy as np
import soundfile as sf
from src.audio_processor import ingest
from src.evaluation import synthesize, synthetic_cases, frame_metrics
from src.pipeline import analyze_file, load_report
from src.schema import AnalysisConfig, PitchTrack
from src.storage import save_correction, content_hash
from src.workspace import Workspace, make_handler
from http.server import ThreadingHTTPServer


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Path('.cache/tests').mkdir(parents=True, exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir='.cache/tests')
        cls.root = Path(cls.temp.name)
        y, cls.reference, cls.truth = synthesize(synthetic_cases()['rests'])
        cls.wav = cls.root/'vocal.wav'
        sf.write(cls.wav, y, 22050, subtype='FLOAT')
        cls.report = analyze_file(cls.wav, cls.root/'out')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_audio_inference_and_export_roundtrip(self):
        import pretty_midi
        r = self.report
        self.assertEqual(len(r['notes']), 3)
        self.assertGreater(r['notes'][1]['start']-r['notes'][0]['end'], .4)
        midi = pretty_midi.PrettyMIDI(str(Path(r['report_path']).parent/'notes.mid'))
        self.assertEqual(len(midi.instruments[0].notes), 3)
        self.assertAlmostEqual(midi.instruments[0].notes[1].start, r['notes'][1]['start'], delta=.003)
        self.assertEqual(r['audio']['content_sha256'], content_hash(self.wav))
        self.assertIsNone(json.loads(Path(r['report_path']).read_text())['raw_pitch']['f0_hz'][0])

    def test_cache_and_manual_work_across_configurations(self):
        out = self.root/'out'
        r = analyze_file(self.wav, out)
        self.assertTrue(r['runtime']['pitch_cache_hit'])
        self.assertTrue(r['runtime']['note_cache_hit'])
        original = json.loads((Path(r['report_path']).parent/'prediction.json').read_text())
        ns = r['notes'];ns[0]['pitch'] = 61
        save_correction(out/'corrections',r['audio']['content_sha256'],ns,r['prediction_id'])
        new = analyze_file(self.wav,out,replace(AnalysisConfig(),confidence=.2))
        self.assertTrue(new['runtime']['pitch_cache_hit'])
        self.assertEqual(new['notes'][0]['pitch'],61)
        self.assertNotEqual(new['predicted_notes'][0]['pitch'],61)
        self.assertEqual(json.loads((Path(r['report_path']).parent/'prediction.json').read_text()),original)

    def test_native_metadata_and_antiphase_stereo(self):
        sr = 44100
        y=.25*np.sin(2*np.pi*440*np.arange(sr)/sr)
        path=self.root/'stereo.flac'
        sf.write(path,np.column_stack((y,-y)),sr)
        signal,meta=ingest(path)
        self.assertEqual(meta.channels,2)
        self.assertEqual(meta.original_sample_rate,44100)
        self.assertEqual(meta.original_samples,44100)
        self.assertAlmostEqual(meta.duration,1.)
        self.assertEqual(len(signal),22050)
        self.assertGreater(float(np.std(signal)),.1)
        mean,_=ingest(path,replace(AnalysisConfig(),channel='mean'))
        self.assertLess(float(np.std(mean)),1e-4)

    def test_mp3_decoding(self):
        if 'MPEG_LAYER_III' not in sf.available_subtypes('MP3'):
            self.skipTest('libsndfile build cannot encode a temporary MP3 fixture')
        sr=44100;y=.25*np.sin(2*np.pi*440*np.arange(sr)/sr)
        path=self.root/'encoded.mp3'
        sf.write(path,y,sr,format='MP3',subtype='MPEG_LAYER_III')
        signal,meta=ingest(path)
        self.assertEqual(meta.original_sample_rate,sr)
        self.assertGreater(len(signal),20000)
        self.assertGreater(float(np.std(signal)),.1)

    def test_real_chunk_boundary_timing(self):
        from src.pitch import estimate_chunked
        sr=22050;y=.25*np.sin(2*np.pi*440*np.arange(sr*4)/sr)
        config=AnalysisConfig(chunk_seconds=2.1,context_seconds=.5)
        track=estimate_chunked(y,sr,config)
        times=np.array(track.times)
        np.testing.assert_allclose(np.diff(times),220/sr,atol=1e-12)
        self.assertLess(times[-1],4.)
        f=np.array([v or np.nan for v in track.f0_hz])
        boundary=np.argmin(abs(times-2.1))
        self.assertTrue(np.all(abs(1200*np.log2(f[boundary-5:boundary+5]/440))<30))

    def test_missing_optional_estimator_is_actionable(self):
        from unittest.mock import patch
        from importlib.metadata import PackageNotFoundError
        from src.pitch import EstimatorUnavailable
        from src import pipeline
        original= pipeline.version
        def missing(name):
            if name=='torch':
                raise PackageNotFoundError(name)
            return original(name)
        with patch('src.pipeline.version', side_effect=missing):
            with self.assertRaisesRegex(EstimatorUnavailable,'optional'):
                analyze_file(self.wav,self.root/'optional',replace(AnalysisConfig(),estimator='torchcrepe'))

    def test_evaluation_does_not_score_human_corrections(self):
        from src.evaluation import evaluate_manifest
        reference=self.root/'reference.json'
        reference.write_text(json.dumps({'notes':[n.to_dict() for n in self.reference]}),encoding='utf-8')
        manifest=self.root/'manifest.json'
        manifest.write_text(json.dumps({'items':[{'audio':self.wav.name,'reference':reference.name,
            'annotator':'synthetic-fixture','convention':'known source seconds; [start,end)'}]}),encoding='utf-8')
        altered=[dict(n) for n in self.report['notes']];altered[0]['pitch']=60
        save_correction(self.root/'evaluation'/'corrections',self.report['audio']['content_sha256'],altered,self.report['prediction_id'])
        results=evaluate_manifest(manifest,self.root/'evaluation')
        self.assertEqual(results[0]['notes']['onset_pitch_offset']['f1'],1.)

    def test_http_review_correction_and_exports(self):
        workspace=Workspace(self.root/'out')
        # Parse real HTTP messages through the handler without a network socket.
        # This also runs inside restricted Windows sandboxes that deny loopback.
        class Socket:
            def __init__(self, request):
                self.request=io.BytesIO(request); self.response=bytearray()
            def makefile(self, *args, **kwargs):
                return self.request
            def sendall(self, data):
                self.response.extend(data)
        def request(path, payload=None, origin='http://127.0.0.1:8765', extra=''):
            body=json.dumps(payload).encode() if payload is not None else b''
            method='POST' if payload is not None else 'GET'
            headers=f'{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:8765\r\nOrigin: {origin}\r\nContent-Length: {len(body)}\r\n{extra}\r\n'
            sock=Socket(headers.encode()+body)
            make_handler(workspace)(sock,('127.0.0.1',1111),SimpleNamespace(server_port=8765))
            header,response=bytes(sock.response).split(b'\r\n\r\n',1)
            return int(header.split()[1]),response
        code,body=request('/')
        self.assertEqual(code,200);self.assertIn(b'Save correction revision',body)
        _,body=request('/api/state');identifier=json.loads(body)['analyses'][0]['id']
        _,body=request('/api/report?id='+identifier);report=json.loads(body)
        code,body=request('/api/audio?id='+identifier,extra='Range: bytes=0-43\r\n')
        self.assertEqual(code,206);self.assertEqual(len(body),44)
        rows=report['notes'];rows[0]['pitch']=63
        code,body=request('/api/correct',{'id':identifier,'notes':rows})
        self.assertEqual(code,200);self.assertEqual(json.loads(body)['notes'][0]['pitch'],63)
        _,body=request('/api/download?id='+identifier+'&type=csv')
        self.assertIn(b'frame_start',body)
        code,_=request('/api/correct',{},origin='https://example.com')
        self.assertEqual(code,403)
