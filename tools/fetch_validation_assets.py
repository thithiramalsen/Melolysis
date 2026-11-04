"""Fetch pinned research assets without redistributing audio, labels or model weights."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import urllib.request
import zipfile

VOCADITO_URL = 'https://zenodo.org/records/5578807/files/vocadito.zip?download=1'
VOCADITO_MD5 = 'dea40fd18f14d899643c4ba221b33a46'
GAME_URL = 'https://github.com/openvpi/GAME/releases/download/v1.0.0/GAME-1.0-small.zip'
GAME_COMMIT = '475a8ee781fe8cca980b3b12fbe6c80c768a813a'


def fetch(url, target, expected_md5=None):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_suffix('.download')
        request = urllib.request.Request(url, headers={'User-Agent':'Melolysis-research/2.1'})
        with urllib.request.urlopen(request, timeout=90) as source, temporary.open('wb') as output:
            shutil.copyfileobj(source, output)
        temporary.replace(target)
    md5 = hashlib.md5(target.read_bytes()).hexdigest()
    if expected_md5 and md5 != expected_md5:
        raise ValueError(f'Checksum mismatch for {target}; retained for inspection')
    return {'url':url,'bytes':target.stat().st_size,'md5':md5,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}


def safe_extract(archive, destination):
    destination = Path(destination).resolve()
    with zipfile.ZipFile(archive) as source:
        if sum(i.file_size for i in source.infolist()) > 1024**3:
            raise ValueError('Research archive exceeds the 1 GiB expanded limit')
        for item in source.infolist():
            name = item.filename.replace('\\','/')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ':' in name or (item.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f'Unsafe archive member: {name}')
            if not (destination / name).resolve().is_relative_to(destination):
                raise ValueError('Archive escapes destination')
        source.extractall(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.cache/research')
    parser.add_argument('--vocadito',action='store_true')
    parser.add_argument('--game-small',action='store_true')
    args = parser.parse_args()
    root = Path(args.root)
    if args.vocadito:
        record = fetch(VOCADITO_URL,root/'vocadito.zip',VOCADITO_MD5)
        record.update(doi='10.5281/zenodo.5578807',version='v3',license='CC-BY-4.0',
            citation='Bittner, Pasalo, Bosch, Meseguer Brocal and Rubinstein (2021), vocadito')
        safe_extract(root/'vocadito.zip',root/'vocadito')
        (root/'vocadito-provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print('Vocadito v3 checksum verified; human annotations and source audio extracted.',flush=True)
    if args.game_small:
        record = fetch(GAME_URL,root/'GAME-1.0-small.zip')
        record.update(license='CC-BY-NC-SA-4.0',release='v1.0.0',code_commit=GAME_COMMIT)
        safe_extract(root/'GAME-1.0-small.zip',root/'GAME-1.0-small')
        (root/'game-provenance.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print('Official GAME small checkpoint extracted; weight license is CC-BY-NC-SA-4.0.',flush=True)


if __name__=='__main__':
    main()
