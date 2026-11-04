# Reproduce the Phase 2 model environment

Tested on Windows, Python 3.12.16, NumPy 1.26.4, PyTorch/torchaudio 2.8.0+cpu,
TorchCREPE 0.0.24 and GAME code v1.0.3. The core Python 3.14 environment remains
separate because GAME requires NumPy <2. The exact model environment is recorded in
[requirements-models-tested.lock.txt](../requirements-models-tested.lock.txt).
The CPU environment contains about **3.60 GiB** of installed files, excluding
Python, downloads and installer caches. Allow additional disk space for those.

## Install on Windows PowerShell

Use an existing Python 3.12 installation, or the tested uv route below. Commands
install only into the project environment/cache. They do not change system PATH
or open windows. Internet access is needed for this explicit setup; normal analysis
does not upload recordings.

```powershell
# Core installation first, as in README.
.\.venv\Scripts\python.exe -m pip install uv==0.13.7
$env:UV_PYTHON_INSTALL_DIR="$PWD\.cache\python"
$env:UV_PYTHON_BIN_DIR="$PWD\.cache\python-bin"
$env:UV_CACHE_DIR="$PWD\.cache\uv"
$env:UV_LINK_MODE='copy'
.\.venv\Scripts\uv.exe python install 3.12.16
.\.venv\Scripts\uv.exe venv .cache/model-env --python 3.12.16
.\.venv\Scripts\uv.exe pip install --python .cache/model-env/Scripts/python.exe torch==2.8.0+cpu torchaudio==2.8.0+cpu --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\uv.exe pip install --python .cache/model-env/Scripts/python.exe -r requirements-models-tested.lock.txt

git clone https://github.com/openvpi/GAME.git .cache/models/GAME
git -C .cache/models/GAME checkout 475a8ee781fe8cca980b3b12fbe6c80c768a813a
.\.venv\Scripts\python.exe tools/fetch_validation_assets.py --game-small --vocadito
.\.venv\Scripts\python.exe tools/import_vocadito.py
```

The second package command reuses the already installed exact CPU torch pair;
use the official CPU index for these two packages if recreating the lock elsewhere.
The complete setup sequence was executed in parts locally; a second clean-machine
installation has not been tested. Linux/macOS need adjusted interpreter paths in
the systems JSON and compatible platform wheels; they were not tested.

GAME code is [MIT](https://github.com/openvpi/GAME/blob/main/LICENSE), but the
[Small checkpoint release](https://github.com/openvpi/GAME/releases/tag/v1.0.0)
is **CC-BY-NC-SA-4.0**. Check its noncommercial/share-alike conditions before use
beyond the present research workflow. Do not infer a weight license from the code
license. TorchCREPE is [MIT](https://github.com/maxrmorrison/torchcrepe).
[Vocadito v3](https://zenodo.org/records/5578807) is CC-BY-4.0; preserve attribution.
Assets are cached locally and not added to Git.

Downloads measured here: GAME archive 46,886,125 bytes (model.pt 50,905,591 bytes),
Vocadito archive 58,492,257 bytes. The fetcher verifies the dataset's published
MD5, bounds archive extraction and records SHA-256/provenance. Keep GAME's
`config.yaml` and `lang_map.json` beside the checkpoint. Tested package-weight
hashes and source/archive identities are in [environment.json](real-vocal/environment.json).

## Run actual comparisons

```powershell
.\.venv\Scripts\python.exe main.py real-evaluate outputs/real-validation/vocadito.manifest.json --systems evaluation/real/systems.validated.json --split development --output outputs/real-validation
.\.venv\Scripts\python.exe main.py real-evaluate outputs/real-validation/vocadito.manifest.json --systems evaluation/real/systems.validated.json --split heldout --output outputs/real-validation
.\.venv\Scripts\python.exe tools/report_real_validation.py
```

The frozen system plan selects **Tiny**, not Full, TorchCREPE. Native CPU runtimes
use two threads, CREPE batch size 128; GAME uses batch size 1 and no data-loader
workers. All three primary systems force real F0/note inference rather than cache
hits. Cold here means no prediction-stage cache, not a flushed OS/JIT file cache.
Each annotation edition reuses the same inference. Derived refinement pins the
successful parent report from the same run. There is no estimator substitution.
Each run archives an immutable results JSON, worker logs, process-tree sampled RSS,
plots and raw reports; the top-level `*-results.json` is only a latest pointer copy.

The checked-in split and experiment plans record development decisions made before
heldout scoring. Do not optimize parameters on heldout scores and keep calling that
split unseen. Reimporting labels preserves source values but generates local
reference IDs/revision timestamps; exact result-file bytes are not expected to match.
Source/annotation hashes and musical scores are the reproducibility targets.

## Analyze your own isolated stem

```powershell
.\.cache\model-env\Scripts\python.exe main.py analyze "data/vocals/MHS Chorus.wav" --note-model game --model-python .cache/model-env/Scripts/python.exe --model-repo .cache/models/GAME --weights .cache/research/GAME-1.0-small/GAME-1.0-small/model.pt --config configs/cpu-analysis.json
# Optional second edition; supply the printed report.json path.
.\.venv\Scripts\python.exe main.py refine-notes path/to/report.json --output outputs
.\.venv\Scripts\python.exe main.py serve --output outputs --port 8770
```

The offset refiner preserves original predictions, expressive contours, onsets,
pitches and note count. It may shorten a quiet unvoiced suffix; compare both editions
and review the change evidence. It is optional, not an automatic correction of truth.
GAME does not emit calibrated note confidence; notes retain a confidence-unavailable
flag. Its F0 display is separately computed pYIN, not a GAME contour.

For standalone TorchCREPE analysis choose `estimator: "torchcrepe"`, `device: "cpu"`,
`pitch_model_capacity: "tiny"` in an AnalysisConfig JSON. Full remains available and
was smoke-tested on one real excerpt; the eight-recording comparison used Tiny.
CUDA was detected as hardware but **not tested**: the installed torch build is CPU
only. Install a compatible CUDA build in a separate environment and benchmark it
before claiming GPU performance. Automatic device selection is implemented, not
evidence of validated GPU accuracy or timing.
