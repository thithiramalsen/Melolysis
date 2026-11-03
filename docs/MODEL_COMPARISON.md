# Model assessment and reproducible comparison

Researched 2026-11-03; implementation verified through 2026-11-04. Repository
documentation is evidence about integration requirements, not independent accuracy
evidence. **Only pYIN performed measured inference in this environment.**

| Candidate | Purpose | Integration status | Measured here |
|---|---|---|---|
| librosa pYIN 0.11.0 | continuous monophonic F0, voicing, voicing probability | default CPU estimator, bounded context chunks | synthetic audio and existing real recording |
| TorchCREPE | continuous F0 and periodicity | lazy optional CPU/CUDA adapter; missing install returns actionable error | dependency absence and error path; no pretrained inference |
| GAME | singing note boundaries and pitches | isolated CLI adapter, model hashes/seed/language/thresholds; MIDI bridge | contracts only; no weights or compatible external environment supplied |
| SOME | singing note extraction | isolated CLI adapter, safe temporary input copy; MIDI bridge | contracts only; no weights supplied |
| Basic Pitch | instrument-agnostic note transcription | lazy cached model adapter, protected mono input, explicit range/thresholds | contracts only; not installed |
| RMVPE | vocal F0 | researched; no direct adapter selected | no inference |

## Selection rationale

pYIN remains the reproducible baseline because it is installed, works on CPU and
exposes voicing evidence without checkpoint downloads. Its probability describes
voicing, not note correctness. The largest confirmed defect was event segmentation,
so the measured comparisons first isolate that stage. This is not a claim that
pYIN is the best estimator for this singer. See the
[librosa pYIN API](https://librosa.org/doc/0.11.0/generated/librosa.pyin.html).

[TorchCREPE](https://github.com/maxrmorrison/torchcrepe) provides tiny/full converted
weights and a periodicity score. The adapter selects full, Viterbi decoding,
bounded batches and automatic CUDA detection, with CPU selectable. Silence is
energy-gated separately. The code is MIT licensed. Its
[package definition](https://github.com/maxrmorrison/torchcrepe/blob/master/setup.py)
requires torch and torchaudio; use a mutually compatible pair. Package-supplied
weights are not downloaded by this application. No local speed, GPU memory or
accuracy claim is available. CUDA requires an appropriate PyTorch build/driver.

[GAME](https://github.com/openvpi/GAME) was prioritized for investigation because
it specifically separates singing boundary detection from pitch estimation.
Upstream documents Python 3.12/PyTorch 2.8 testing and external checkpoints. Its
[requirements](https://github.com/openvpi/GAME/blob/main/requirements.txt) include
NumPy <2, incompatible with this installed NumPy 2.4.4 environment. We therefore
provide a process-isolated bridge rather than downgrade the application.
[GAME code is MIT](https://github.com/openvpi/GAME/blob/main/LICENSE), while
[the 1.0 pretrained weights are CC BY-NC-SA 4.0](https://github.com/openvpi/GAME/releases/tag/v1.0.0).
Code licensing does not grant a different license for weights. Upstream lists
roughly 12M/50M/100M parameter variants; FP32 parameter storage alone would be
approximately 48/200/400 MB, an estimate excluding activations, optimizer/checkpoint
extras and runtime. Actual download sizes, RAM/VRAM and CPU throughput were not
measured. Preserve config.yaml and any language map beside the checkpoint.

[SOME](https://github.com/openvpi/SOME) documents PyTorch >=2.1 and CPU/GPU use.
It points users to GAME as its successor. Its code is MIT, but
[released model files are CC BY-NC-SA 4.0](https://github.com/openvpi/SOME/releases).
The adapter invokes only the single-file inference path on a temporary copy;
the upstream dataset-overwrite command is never used. Third-party performance
numbers were not adopted as measurements here.

[Basic Pitch](https://github.com/spotify/basic-pitch) is Apache-2.0 and ships
multiple model formats. Its documented Python support stops at 3.11, and its
Windows runtime routing differs by Python version. Use an isolated supported
environment or import its MIDI rather than assuming Python 3.14 compatibility.
It is not singing-specific and may emit polyphony. The adapter refuses overlapping
lead-melody events instead of silently choosing a voice. Note-event velocity is
**amplitude, not confidence**; imported notes are explicitly flagged as lacking
correctness confidence. Timing/window compensation remains the upstream API's
responsibility; verify against source-time labels before using it as a baseline.

[Original RMVPE](https://github.com/Dream-High/RMVPE) is Apache-2.0 research code.
[The yxlllc implementation](https://github.com/yxlllc/RMVPE) has a separate training,
export and checkpoint ecosystem. We did not establish a maintained packaged API,
verified checkpoint license/version and compatible local runtime together, so no
unverified downloader or guessed integration is included. GAME/SOME may manage
their own pitch backend; record that model's configuration too.

## Installation of optional backends

Keep external checkouts and environments under a directory you manage; never put
their requirements into the core venv. The following are setup examples, **not a
record of successful local installation**:

```powershell
# In a separately created supported Python environment, using its own python:
python -m pip install torchcrepe
# Install the matching PyTorch/torchaudio CPU or CUDA builds per upstream first.

# GAME/SOME: clone their official repository; install its requirements in its own
# supported environment. Download a checkpoint from the official release page,
# inspect its weight license, and retain companion configuration files.
```

Example bridge invocation (replace the three external paths):

```powershell
.\.venv\Scripts\python.exe main.py analyze "data/vocals/MHS Chorus.wav" --note-model game --model-python "D:/models/game-env/Scripts/python.exe" --model-repo "D:/models/GAME" --weights "D:/models/GAME/checkpoint/model.ckpt"
```

GAME language, boundary/presence thresholds and seed can be supplied through
AnalysisConfig JSON (`model_language`, `model_boundary_threshold`,
`model_presence_threshold`, `model_seed`). The bridge seeds Python/NumPy/Torch;
bitwise GPU determinism is not promised. The external CLI controls device selection
through its own runtime; the F0 estimator's device option does not configure it.
External models cold-load once per uncached recording; that startup is not yet
amortized in a persistent worker. Basic Pitch models are cached in-process.

Record the external repository commit, checkpoint/config hashes, environment
freeze, language, device and exact command for a publishable comparison. Current
provenance hashes weights and companion configuration and records repository
commit/infer.py hash. Changes to other uncommitted external files require a clean
checkout or manual cache invalidation. No model downloads occur implicitly.

## Reproducible evaluation protocol

1. Install `requirements-eval.txt` and run both synthetic suites from README.
2. Independently annotate real vocal excerpts using the convention in
   `evaluation/reference_manifest.example.json`. Split development/test by song;
   avoid using the same corrected excerpt for tuning and final claims.
3. Run `evaluate` with the **same manifest** for each note model. This evaluates
   `predicted_notes`, even if human corrections exist; corrections cannot leak into
   prediction scores. Optional reference F0 enables frame metrics.
4. Check timestamp alignment using a known attack before scoring. Apply an explicit
   `--timestamp-offset` on analysis/import only when independently justified; never
   search offsets to improve reported test scores.
5. Keep per-case scores, annotation conventions and failures. Do not infer model
   superiority from the current synthetic benchmark or from plausible plots.

Imported predictions can also be compared without installing their frameworks:

```powershell
.\.venv\Scripts\python.exe main.py analyze "vocal.wav" --note-model game --import-midi "game-result.mid"
```

Import preserves MIDI seconds (including tempo-map timing) and marks missing
confidence. MIDI quantizes pitch; full model confidence/float scores are not
preserved by this bridge. Raw continuous pYIN/TorchCREPE F0 remains a separate
representation. See [EVALUATION.md](EVALUATION.md) for actual measurements.
