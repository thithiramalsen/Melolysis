import os
import random
import numpy as np
import soundfile as sf
from src.audio_processor import load_audio, extract_pitch, midi_conversion
from src.analyzer import extract_features, print_report
from src.generator import build_markov_model, generate_melody, save_midi
from src.visualization import plot_pitch_contour, plot_interval_histogram

def generate_dummy_audio(filepath):
    """Generates a dummy sine wave audio file for demonstration."""
    print(f"Creating dummy audio file at {filepath}...")
    sr = 22050
    duration = 5 # seconds
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Simple melody: C4, E4, G4, C5, G4, E4, C4 (repeated)
    freqs = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63, 261.63] * 2
    samples_per_note = int(sr * duration / len(freqs))
    
    y = np.concatenate([np.sin(2 * np.pi * f * np.linspace(0, duration / len(freqs), samples_per_note)) for f in freqs])
    sf.write(filepath, y, sr)

def main():
    # 1. Configuration
    audio_dir = os.path.join("data", "vocals")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, "input_vocals.wav")
    output_dir = "data"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate dummy file if none exists
    if not os.path.exists(audio_path):
        print(f"Warning: '{audio_path}' not found.")
        generate_dummy_audio(audio_path)

    # Pipeline Steps 1-2. Load audio and extract pitch
    y, sr = load_audio(audio_path)
    f0 = extract_pitch(y, sr)
    
    # 3-4. Convert to MIDI notes and segment
    discrete_notes = midi_conversion(f0)
    if not discrete_notes:
        print("Error: No valid pitches found in the audio. Exiting.")
        return
        
    print(f"-> Extracted {len(discrete_notes)} discrete note events.")

    # 5-6. Extract features and print report
    report = extract_features(discrete_notes)
    print_report(report)
    
    # 10. Visualization (Optional)
    plot_pitch_contour(report["raw_pitches"], os.path.join(output_dir, "pitch_contour.png"))
    plot_interval_histogram(report["raw_intervals"], os.path.join(output_dir, "interval_histogram.png"))

    # 7. Build Markov Model
    markov_model = build_markov_model(discrete_notes)
    
    # 8. Generate a new melody
    start_note = random.choice(report["raw_pitches"])
    new_melody = generate_melody(
        markov_model, 
        start_note=start_note, 
        min_pitch=report["pitch_min"], 
        max_pitch=report["pitch_max"],
        length=30, # Generate 30 notes
        max_jump=5 # Keep interval jumps <= 5 semitones
    )
    
    print(f"\nGenerated sequence (MIDI notes): {new_melody}")
    
    # 9. Save to MIDI file
    output_midi_path = os.path.join(output_dir, "generated_melody.mid")
    
    # Assign realistic durations based on the average duration frames
    # Simple heuristic to translate frames to seconds (approx. 0.25s base)
    save_midi(new_melody, output_midi_path, duration_sec=0.25)
    
    print("\nPipeline execution complete! Check the 'data' folder for outputs.")

if __name__ == "__main__":
    main()
