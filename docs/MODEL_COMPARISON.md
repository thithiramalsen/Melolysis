# Model assessment and reproducible comparison

Researched 2026-11-03; implementation verified through 2026-11-04. Repository
documentation is evidence about integration requirements, not independent accuracy
evidence. Phase 2 now includes **actual pretrained GAME and TorchCREPE inference**,
not only adapter tests. [Real-vocal measurements](REAL_VOCAL_VALIDATION.md) retain
both published human editions and four heldout singers.

| Candidate | Purpose | Integration status | Measured here |
|---|---|---|---|
| librosa pYIN 0.11.0 | continuous monophonic F0, voicing, voicing probability | default CPU estimator, bounded context chunks | synthetic audio and existing real recording |
| TorchCREPE 0.0.24 | continuous F0 and periodicity | lazy CPU/CUDA adapter, explicit capacity/batches/native timing, deterministic Viterbi centers | Tiny on 8 published real excerpts + private MHS; Full on 1 public development excerpt; CPU only |
| GAME v1.0.3 / Small 1.0 | singing note boundaries and pitches | isolated pretrained CLI, float CSV, weight/config hashes/seed/language/thresholds | 8 published real excerpts + private MHS; CPU only; private accuracy unvalidated |
| SOME | singing note extraction | isolated CLI adapter, safe temporary input copy; MIDI bridge | contracts only; no weights supplied |
| Basic Pitch | instrument-agnostic note transcription | lazy cached model adapter, protected mono input, explicit range/thresholds | contracts only; not installed |
| RMVPE | vocal F0 | researched; no direct adapter selected | no inference |

## Selection rationale

pYIN remains the default and baseline; its probability describes voicing, not note
correctness. On heldout recordings, TorchCREPE Tiny improves continuous RPA while
its unchanged heuristic note segmenter performs worse. GAME improves onset+pitch
F1 for both human editions; offset-aware ranking depends on edition. Optional
acoustic tail refinement improves GAME on heldout without changing pitch/onsets.
No universal model winner or private-singer accuracy is established. See the
[librosa pYIN API](https://librosa.org/doc/0.11.0/generated/librosa.pyin.html).

[TorchCREPE](https://github.com/maxrmorrison/torchcrepe) provides tiny/full converted
weights and a periodicity score. The adapter defaults to Full, with Tiny explicitly
selected in the practical CPU comparison; it uses Viterbi decoding,
bounded batches and automatic CUDA detection, with CPU selectable. Silence is
energy-gated separately. The code is MIT licensed. Its
[package definition](https://github.com/maxrmorrison/torchcrepe/blob/master/setup.py)
requires torch and torchaudio; use a mutually compatible pair. Package-supplied
weights come with torchcrepe installation. Measured CPU speed and sampled process
RSS are in the real-vocal report; GPU execution was not tested. The adapter removes
upstream random ±20-cent triangular conversion dither and records this model
identity. CUDA requires an appropriate PyTorch build/driver.

[GAME](https://github.com/openvpi/GAME) was prioritized for investigation because
it specifically separates singing boundary detection from pitch estimation.
Upstream documents Python 3.12/PyTorch 2.8 testing and external checkpoints. Its
[requirements](https://github.com/openvpi/GAME/blob/main/requirements.txt) include
NumPy <2, incompatible with this installed NumPy 2.4.4 environment. We therefore
use a Python 3.12.16 / NumPy 1.26.4 process-isolated environment rather than
downgrade the core application. Tested torch/torchaudio are 2.8.0+cpu.
[GAME code is MIT](https://github.com/openvpi/GAME/blob/main/LICENSE), while
[the 1.0 pretrained weights are CC BY-NC-SA 4.0](https://github.com/openvpi/GAME/releases/tag/v1.0.0).
Code licensing does not grant a different license for weights. Upstream lists
roughly 12M/50M/100M parameter variants; FP32 parameter storage alone would be
approximately 48/200/400 MB, an estimate excluding activations, optimizer/checkpoint
extras and runtime. Small's actual archive is 46,886,125 bytes; model.pt is
50,905,591 bytes. Measured worker wall/RSS includes the pYIN display contour and
external GAME child, not only neural compute. Preserve config.yaml and any language
map beside the checkpoint. No GPU memory result is available.

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

Keep external checkouts and environments separate from the core venv.
[MODEL_SETUP.md](MODEL_SETUP.md) records the successfully installed isolated CPU
environment, pinned upstream commit/checkpoint, exact packages, downloads and
commands. The following generic examples are retained for other optional backends:

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
bitwise GPU determinism is not promised. `device: "cpu"` also hides CUDA from the
external child; otherwise the external CLI controls selection through its runtime.
External models cold-load once per uncached recording; that startup is not yet
amortized in a persistent worker. Basic Pitch models are cached in-process.

Record the external repository commit, checkpoint/config hashes, environment
freeze, language, device and exact command for a publishable comparison. Current
provenance hashes weights and companion configuration and records repository
commit/infer.py hash. Changes to other uncommitted external files require a clean
checkout or manual cache invalidation. No model downloads occur implicitly.

## Reproducible evaluation protocol

1. Install `requirements-eval.txt` and run both synthetic suites from README.
2. Use the independent reference editor and [annotation protocol](ANNOTATION_PROTOCOL.md),
   or import the published Vocadito annotations. Assign source/song/singer groups
   before tuning and reserve heldout groups. Freeze reviewed revisions/checksums.
3. Use `real-evaluate` with the same frozen manifest and system plan for each split.
   It rejects drafts/source changes/split leakage and always scores raw
   `predicted_notes`. Published F0 enables frame metrics; flat symbolic notes alone
   do not establish expressive pitch truth. The legacy `evaluate` command does not
   enforce the newer review/split gates.
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
preserved by MIDI import. Actual GAME inference now uses its float CSV rather than
MIDI; onset, offset and fractional pitch are retained. Raw pYIN/TorchCREPE F0 remains a separate
representation. See [EVALUATION.md](EVALUATION.md) for actual measurements.
