import matplotlib.pyplot as plt
import numpy as np
import os

def plot_pitch_contour(raw_pitches, filepath="data/pitch_contour.png"):
    """Plots the pitch contour of the analyzed melody."""
    print(f"Plotting pitch contour to '{filepath}'...")
    plt.figure(figsize=(10, 4))
    plt.plot(raw_pitches, marker='.', linestyle='-', color='indigo', alpha=0.7)
    plt.title('Melody Pitch Contour')
    plt.xlabel('Note Event Index')
    plt.ylabel('MIDI Note')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()

def plot_interval_histogram(raw_intervals, filepath="data/interval_histogram.png"):
    """Plots a histogram of the interval distribution."""
    print(f"Plotting interval histogram to '{filepath}'...")
    plt.figure(figsize=(8, 4))
    
    # Calculate sensible bins for intervals
    if len(raw_intervals) > 0:
        min_int = int(min(raw_intervals))
        max_int = int(max(raw_intervals))
    else:
        min_int, max_int = -12, 12
        
    bins = np.arange(min_int - 0.5, max_int + 1.5, 1)
    
    plt.hist(raw_intervals, bins=bins, color='teal', edgecolor='black', alpha=0.7)
    plt.title('Interval Distribution (Steps/Jumps)')
    plt.xlabel('Interval (Semitones)')
    plt.ylabel('Frequency')
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()
