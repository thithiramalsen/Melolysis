import numpy as np
from collections import defaultdict, Counter
import pretty_midi

def build_markov_model(notes):
    """Builds a Markov chain from the note sequence."""
    print("Building Markov model...")
    pitches = [n["pitch"] for n in notes]
    
    # Map state (current note) to counts of next notes
    transitions_count = defaultdict(list)
    for i in range(len(pitches) - 1):
        current_note = pitches[i]
        next_note = pitches[i+1]
        transitions_count[current_note].append(next_note)
        
    # Convert counts to transition probabilities
    markov_model = {}
    for state, transitions in transitions_count.items():
        counts = Counter(transitions)
        total = sum(counts.values())
        probabilities = {next_state: count / total for next_state, count in counts.items()}
        markov_model[state] = probabilities
        
    return markov_model

def generate_melody(markov_model, start_note, min_pitch, max_pitch, length=30, max_jump=5):
    """Generates a new melody using the Markov chain."""
    print("Generating new melody based on Markov chain...")
    generated_notes = [start_note]
    current_note = start_note
    
    for _ in range(length - 1):
        if current_note in markov_model:
            transitions = markov_model[current_note]
            
            # Constraints: limit jumps and stay within pitch range
            valid_notes = []
            valid_probs = []
            
            for next_note, prob in transitions.items():
                if abs(next_note - current_note) <= max_jump and min_pitch <= next_note <= max_pitch:
                    valid_notes.append(next_note)
                    valid_probs.append(prob)
                    
            if valid_notes:
                # Normalize probabilities
                total_prob = sum(valid_probs)
                valid_probs = [p / total_prob for p in valid_probs]
                next_note = np.random.choice(valid_notes, p=valid_probs)
            else:
                # Fallback: random valid step
                step = np.random.choice(range(-max_jump, max_jump + 1))
                next_note = np.clip(current_note + step, min_pitch, max_pitch)
        else:
            # Fallback if state has no known transitions
            step = np.random.choice(range(-max_jump, max_jump + 1))
            next_note = np.clip(current_note + step, min_pitch, max_pitch)
            
        generated_notes.append(next_note)
        current_note = next_note
        
    return generated_notes

def save_midi(generated_notes, filepath, duration_sec=0.3):
    """Converts the generated melody to a MIDI file using pretty_midi."""
    print(f"Saving generated melody to '{filepath}'...")
    pm = pretty_midi.PrettyMIDI()
    
    # Program 52 is Choir Aahs, a vocal-like instrument
    inst = pretty_midi.Instrument(program=52)
    
    start_time = 0.0
    for pitch in generated_notes:
        note = pretty_midi.Note(
            velocity=100,
            pitch=int(pitch),
            start=start_time,
            end=start_time + duration_sec
        )
        inst.notes.append(note)
        start_time += duration_sec
        
    pm.instruments.append(inst)
    pm.write(filepath)
