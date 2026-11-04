"""Import the two published musician note editions and corrected F0 without inventing labels."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import soundfile as sf
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.references import ReferenceStore
from src.schema import NoteEvent,PitchTrack
from src.storage import content_hash,write_json


def import_vocadito(data,workspace,plan_path):
    data,workspace=Path(data).resolve(),Path(workspace).resolve()
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'))
    metadata={int(row['track_id']):row for row in csv.DictReader((data/'vocadito_metadata.csv').open(encoding='utf-8'))}
    store=ReferenceStore(workspace/'references');identifiers=[];singers={}
    for split in ('development','heldout'):
        for track_id in plan[split]:
            m=metadata[track_id];singer=m['singer_id']
            if singer in singers and singers[singer]!=split:
                raise ValueError('Frozen split leaks a singer between subsets')
            singers[singer]=split
            wav=data/'Audio'/f'vocadito_{track_id}.wav';info=sf.info(wav)
            audio={'source_path':str(wav),'content_sha256':content_hash(wav),
                'original_sample_rate':info.samplerate,'original_samples':info.frames,'channels':info.channels,
                'sample_rate':info.samplerate,'samples':info.frames,'duration':info.frames/info.samplerate,
                'decoder':'soundfile.info','channel_policy':'published-mono','input_kind':'isolated_vocal'}
            f0_path=data/'Annotations'/'F0'/f'vocadito_{track_id}_f0.csv'
            f0=np.loadtxt(f0_path,delimiter=',',ndmin=2);valid=f0[:,1]>0
            pitch=PitchTrack(f0[:,0].tolist(),[float(f) if f>0 else None for f in f0[:,1]],valid.tolist(),
                valid.astype(float).tolist(),[1.]*len(f0),'vocadito-published-human-corrected-f0',float(np.median(np.diff(f0[:,0]))))
            from dataclasses import asdict
            for edition in plan['annotations']:
                annotation=data/'Annotations'/'Notes'/f'vocadito_{track_id}_notes{edition}.csv'
                labels=np.loadtxt(annotation,delimiter=',',ndmin=2)
                notes=[NoteEvent(f'vocadito-{track_id}-{edition}-{i}',float(a),float(a+d),float(69+12*np.log2(f/440)),1.).to_dict()
                       for i,(a,f,d) in enumerate(labels)]
                convention=('Published Tony note edition '+edition+'; source-second onset and duration; pitch supplied in Hz; '
                    'publisher musician piano-style segmentation; A1 and A2 retained separately, no best-reference selection')
                ref=store.import_published({'format':'melolysis-human-reference-v1','audio':audio,
                    'excerpt':{'start':0.,'end':audio['duration'],'start_sample':0,'end_sample':info.frames,'sample_rate':info.samplerate},
                    'notes':notes,'pitch':asdict(pitch),'regions':[],'annotator':f'Published Vocadito annotator {edition}',
                    'protocol':'vocadito-published-2021','split':split,'song_group':'vocadito-singer-'+singer,
                    'origin':{'kind':'published_human_dataset','dataset':'vocadito-v3','track':track_id,'edition':edition,
                        'citation':'Bittner, Pasalo, Bosch, Meseguer Brocal and Rubinstein (2021), vocadito, DOI 10.5281/zenodo.5578807',
                        'license':'CC-BY-4.0','annotation_sha256':content_hash(annotation),'f0_sha256':content_hash(f0_path),
                        'convention':convention,'independent_of_melolysis':True,'new_user_review':False},
                    'review':{'status':'reviewed','reviewer':f'Vocadito published musician {edition}',
                        'kind':'published_human_annotation','attestation':False},
                    'metadata':{'artist':'Vocadito '+singer,'song':f'vocadito_{track_id}','section':'excerpt','language':m['language']}})
                identifiers.append(ref['id'])
    manifest=store.export_manifest(workspace/'real-validation'/'vocadito.manifest.json',identifiers)
    manifest.update(dataset='vocadito-v3',split_plan_sha256=content_hash(plan_path),
        selection_policy=plan['selection'],pretrained_training_overlap='unknown')
    write_json(workspace/'real-validation'/'vocadito.manifest.json',manifest)
    print(f'Imported {len(identifiers)} published annotation editions for {len(singers)} real singers; no new human labels were authored.')
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',default='.cache/research/vocadito')
    parser.add_argument('--workspace',default='outputs')
    parser.add_argument('--plan',default='evaluation/real/vocadito_split.json')
    args=parser.parse_args();import_vocadito(args.data,args.workspace,args.plan)
