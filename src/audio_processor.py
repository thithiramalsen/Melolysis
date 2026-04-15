import librosa
import numpy as np

def load_audio(filepath, sr=22050):
    """Loads an audio file and returns the signal and sample rate."""
    print(f"Loading '{filepath}'...")
    y, sr = librosa.load(filepath, sr=sr)
    return y, sr

def extract_pitch(y, sr):
    """Extracts the fundamental frequency (pitch) using librosa.pyin."""
    print("Extracting pitch (this may take a moment)...")
    fmin = librosa.note_to_hz('C2')
    fmax = librosa.note_to_hz('C7')
    f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=sr)
    return f0

def midi_conversion(f0):
    """Converts pitch (Hz) to MIDI notes, cleans NaNs, and segments into discrete events."""
    print("Converting to MIDI notes and segmenting...")
    
    # Clean NaN values
    valid_f0 = f0[~np.isnan(f0)]
    if len(valid_f0) == 0:
        return []
    
    # Convert Hz to MIDI floats, then round to nearest integer
    midi_float = librosa.hz_to_midi(valid_f0)
    midi_notes = np.round(midi_float).astype(int)
    
    # Segment notes into discrete note events (merge sustained pitches)
    discrete_notes = []
    if len(midi_notes) > 0:
        current_note = midi_notes[0]
        duration = 1
        for note in midi_notes[1:]:
            if note == current_note:
                duration += 1
            else:
                discrete_notes.append({"pitch": current_note, "duration": duration})
                current_note = note
                duration = 1
        discrete_notes.append({"pitch": current_note, "duration": duration})
    
    return discrete_notes
