"""Deterministic stage cache and independent, versioned human corrections."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .schema import PIPELINE_VERSION, notes_from_dicts


def content_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def key_for(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class StageCache:
    def __init__(self, root):
        self.root = Path(root)

    def path(self, stage, identity):
        return self.root / stage / (key_for([PIPELINE_VERSION, identity]) + ".json")

    def get(self, stage, identity):
        try:
            return json.loads(self.path(stage, identity).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def put(self, stage, identity, value):
        write_json(self.path(stage, identity), value)


def save_correction(root, source_hash, notes, base_prediction, author="user"):
    from datetime import datetime, timezone
    from uuid import uuid4
    rows = [n.to_dict() if hasattr(n, "to_dict") else n for n in notes]
    validated = notes_from_dicts(rows)
    revision = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    value = {"source_hash": source_hash, "base_prediction": base_prediction,
             "author": author, "revision": revision, "notes": [n.to_dict() for n in validated]}
    write_json(Path(root) / source_hash / (revision + ".json"), value)
    return value


def latest_correction(root, source_hash):
    paths = sorted((Path(root) / source_hash).glob("*.json"))
    if not paths:
        return None
    value = json.loads(paths[-1].read_text(encoding="utf-8"))
    if value["source_hash"] != source_hash:
        raise ValueError("Correction source mismatch")
    notes_from_dicts(value["notes"])
    return value
