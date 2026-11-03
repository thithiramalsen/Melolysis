"""Melolysis entry point. Existing file discovery remains available to callers."""
import os
from src.audio_processor import SUPPORTED_AUDIO_EXTENSIONS


def find_audio_file(audio_dir):
    """Return the first supported audio file by filename, preserving the existing API."""
    if not os.path.isdir(audio_dir):
        return None
    files = sorted(os.path.join(audio_dir, filename) for filename in os.listdir(audio_dir)
                   if filename.lower().endswith(SUPPORTED_AUDIO_EXTENSIONS)
                   and os.path.isfile(os.path.join(audio_dir, filename)))
    if len(files) > 1:
        print(f"Multiple audio files found; using '{files[0]}'.")
    return files[0] if files else None


def generate_dummy_audio(filepath):
    """Explicit legacy demo helper; never called as a substitute for missing input."""
    import soundfile as sf
    from src.evaluation import synthesize, synthetic_cases
    y, _, _ = synthesize(synthetic_cases()['stepwise'])
    sf.write(filepath, y, 22050)


if __name__ == '__main__':
    from src.cli import main
    raise SystemExit(main())
