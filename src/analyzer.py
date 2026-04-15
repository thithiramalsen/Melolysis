import numpy as np
from collections import Counter

def extract_features(notes):
    """Extracts analytical features from a sequence of discrete note events."""
    print("Extracting features...")
    if not notes:
        return {}
    
    pitches = [n["pitch"] for n in notes]
    durations = [n["duration"] for n in notes]
    
    # Interval distribution (difference between consecutive notes)
    intervals = np.diff(pitches)
    
    # Percentage of stepwise motion (interval <= 2 semitones)
    if len(intervals) > 0:
        stepwise_count = np.sum(np.abs(intervals) <= 2)
        stepwise_percentage = (stepwise_count / len(intervals)) * 100
        jump_percentage = 100 - stepwise_percentage
        avg_interval = np.mean(np.abs(intervals))
    else:
        stepwise_percentage = 0
        jump_percentage = 0
        avg_interval = 0
        
    # Pitch range (max - min MIDI note)
    pitch_min = np.min(pitches)
    pitch_max = np.max(pitches)
    pitch_range = pitch_max - pitch_min
    
    # Contour (sequence of up/down/same movements)
    contour = []
    for interval in intervals:
        if interval > 0:
            contour.append('U') # Up
        elif interval < 0:
            contour.append('D') # Down
        else:
            contour.append('S') # Same
            
    # Motif detection (repeated 3-note sequences)
    motifs = []
    for i in range(len(pitches) - 2):
        motif = tuple(pitches[i:i+3])
        motifs.append(motif)
    motif_counts = Counter(motifs)
    most_common_motifs = motif_counts.most_common(5) # Top 5 motifs
    
    # Rhythm: average note duration
    avg_duration = np.mean(durations)
    
    # Compile report
    report = {
        "average_interval": avg_interval,
        "stepwise_percentage": stepwise_percentage,
        "jump_percentage": jump_percentage,
        "pitch_min": int(pitch_min),
        "pitch_max": int(pitch_max),
        "pitch_range": int(pitch_range),
        "most_common_motifs": most_common_motifs,
        "average_duration": avg_duration,
        "raw_intervals": intervals.tolist(),
        "raw_pitches": pitches
    }
    
    return report

def print_report(report):
    """Prints a structured analysis report."""
    print("\n" + "="*35)
    print("      MELODY ANALYSIS REPORT")
    print("="*35)
    print(f"Pitch Range: {report['pitch_range']} semitones ({report['pitch_min']} to {report['pitch_max']})")
    print(f"Average Interval: {report['average_interval']:.2f} semitones")
    print(f"Stepwise Motion (<=2 semitones): {report['stepwise_percentage']:.1f}%")
    print(f"Jump Motion (>2 semitones): {report['jump_percentage']:.1f}%")
    print(f"Average Note Duration: {report['average_duration']:.2f} frames")
    print("\nMost Common 3-Note Motifs (MIDI notes):")
    for i, (motif, count) in enumerate(report['most_common_motifs'], 1):
        print(f"  {i}. {motif}: {count} times")
    print("="*35 + "\n")
