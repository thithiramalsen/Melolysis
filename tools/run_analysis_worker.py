"""One real inference job, isolated for honest wall time / sampled process RSS."""
import json
import os
from pathlib import Path
import sys
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from src.schema import AnalysisConfig
from src.pipeline import analyze_file
from src.storage import write_json


if __name__=='__main__':
    job=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    try:
        # No Torch import in baseline workers; native thread limits are inherited.
        if job.get('parent_report') and job['system'].get('refine_from'):
            from src.note_refinement import refine_report
            report=refine_report(job['parent_report'],job['output'],job['system'].get('refinement_config'))
        elif job.get('parent_report'):
            from src.resegmentation import resegment_report
            report=resegment_report(job['parent_report'],job['output'],job['system']['config_overrides'])
        else:
            report=analyze_file(job['audio'],job['output'],AnalysisConfig(**job['system'].get('config',{})),
                metadata=job.get('metadata'),note_model=job['system'].get('note_model','heuristic'),
                model_python=job['system'].get('model_python'),model_repo=job['system'].get('model_repo'),
                weights=job['system'].get('weights'),timestamp_offset=job['system'].get('timestamp_offset',0.),
                use_cache=not job['system'].get('force_inference',False))
        write_json(job['result'],{'status':'success','report_path':report['report_path'],'runtime':report['runtime']})
    except Exception as exc:
        write_json(job['result'],{'status':'failed','error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc()})
        traceback.print_exc();raise SystemExit(1)
