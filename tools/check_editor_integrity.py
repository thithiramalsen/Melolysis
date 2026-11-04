"""Read-only regression scoring; never rerun inference or rewrite frozen results."""
import hashlib
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.real_evaluation import read_manifest
from src.real_metrics import score_reference


def check(snapshot_path='.cache/ux/protected-before.json',output_path='.cache/ux/evaluation-regression.json'):
    snapshot=json.loads(Path(snapshot_path).read_text(encoding='utf-8'))
    changed=[name for name,sha in snapshot.items() if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=sha]
    if changed:raise RuntimeError('Protected files changed: '+repr(changed))
    _,items=read_manifest('outputs/real-validation/vocadito.manifest.json')
    references={r['id']:r for _,r,_ in items};count=0
    for split in ('development','heldout'):
        previous=json.loads(Path(f'docs/real-vocal/{split}.json').read_text(encoding='utf-8'))
        for record in previous['records']:
            if record['status']=='model_unavailable':continue
            report=json.loads(Path(record['report_path']).read_text(encoding='utf-8'))
            fresh=score_reference(references[record['reference_id']],report)
            for key,value in fresh.items():
                # mir_eval must be installed in this environment for an exact comparison.
                if json.dumps(value,sort_keys=True)!=json.dumps(record[key],sort_keys=True):
                    raise RuntimeError(f'Metric mismatch: {split}/{record["system"]}/{record["reference_id"]}/{key}')
            count+=1
    result={'scored_records':count,'all_scoring_outputs_identical':True,'protected_files_unchanged':len(snapshot),
        'frozen_manifest_revalidated':True,'mhs_user_reference_touched':False,
        'scope':'Re-scored stored predictions using frozen references; no inference rerun or benchmark modification.'}
    output=Path(output_path);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--snapshot',default='.cache/ux/protected-before.json');parser.add_argument('--output',default='.cache/ux/evaluation-regression.json')
    args=parser.parse_args();check(args.snapshot,args.output)
