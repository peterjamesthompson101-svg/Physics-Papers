#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Black Hole Phase Memory Reader v2.0
Harmonic Framework Implementation
Paper 30: The Black Hole Information Paradox as Phase Memory

NOW WITH REAL DATA INPUT CAPABILITY
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, TextBox
from scipy.fft import fft, fftfreq
from scipy.signal import find_peaks, spectrogram
from scipy.stats import norm
import json
import os
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# ============================================================================
# HARMONIC FRAMEWORK CONSTANTS
# ============================================================================

F0 = 27.0
PHI_0 = -1.0
PHI_0_RAD = np.radians(PHI_0)
RATIO_19_13 = 19.0 / 13.0
RATIO_13_4 = 13.0 / 4.0
CUTOFF_230 = 230
N_HARMONICS = 32
C = 299792458.0
H = 6.62607015e-34
G = 6.67430e-11
M_SUN = 1.98847e30
K_B = 1.380649e-23

# ============================================================================
# REAL DATA INPUT HANDLERS
# ============================================================================

class DataLoader:
    """Load and preprocess real observational data."""
    
    @staticmethod
    def load_fits(filename):
        """Load FITS file data (radio telescopes, X-ray)."""
        try:
            from astropy.io import fits
            data = fits.getdata(filename)
            header = fits.getheader(filename)
            return {'data': data, 'header': header, 'type': 'fits'}
        except ImportError:
            print("⚠️ Astropy not installed. Install with: pip install astropy")
            return None
        except Exception as e:
            print(f"⚠️ Error loading FITS: {e}")
            return None
    
    @staticmethod
    def load_csv(filename, time_col=0, data_col=1):
        """Load CSV data (time, frequency, amplitude)."""
        try:
            import pandas as pd
            df = pd.read_csv(filename)
            time = df.iloc[:, time_col].values
            data = df.iloc[:, data_col].values
            return {'time': time, 'data': data, 'type': 'csv'}
        except ImportError:
            print("⚠️ Pandas not installed. Install with: pip install pandas")
            return None
        except Exception as e:
            print(f"⚠️ Error loading CSV: {e}")
            return None
    
    @staticmethod
    def load_npy(filename):
        """Load NumPy binary data."""
        try:
            data = np.load(filename)
            return {'data': data, 'type': 'npy'}
        except Exception as e:
            print(f"⚠️ Error loading NPY: {e}")
            return None
    
    @staticmethod
    def load_json(filename):
        """Load JSON data (spectral time series)."""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            return {'data': data, 'type': 'json'}
        except Exception as e:
            print(f"⚠️ Error loading JSON: {e}")
            return None
    
    @staticmethod
    def simulate_data(duration=10.0, sample_rate=1000.0, mass_solar=10.0):
        """
        Generate simulated data based on harmonic framework.
        Useful for testing without real data.
        """
        t = np.arange(0, duration, 1/sample_rate)
        
        # Fundamental frequency for the black hole
        f_fundamental = K_B * black_hole_temperature(mass_solar) / H
        
        # Generate harmonic comb
        signal = np.zeros_like(t)
        for k in range(1, N_HARMONICS + 1):
            freq = k * f_fundamental
            amplitude = 1.0 / k
            phase = k * PHI_0_RAD
            signal += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        # Add noise
        noise_level = 0.1 * np.std(signal)
        signal += np.random.normal(0, noise_level, len(t))
        
        return {'time': t, 'data': signal, 'type': 'simulated'}

# ============================================================================
# REAL SIGNAL PROCESSING
# ============================================================================

class SignalProcessor:
    """Process real data to detect harmonic signatures."""
    
    def __init__(self):
        self.sample_rate = None
        self.time = None
        self.data = None
        self.spectrum = None
        self.frequencies = None
        
    def load_data(self, data_dict):
        """Load data from dictionary."""
        if data_dict is None:
            return False
        
        if 'time' in data_dict and 'data' in data_dict:
            self.time = data_dict['time']
            self.data = data_dict['data']
            self.sample_rate = 1.0 / (self.time[1] - self.time[0])
            return True
        elif 'data' in data_dict:
            # Assume uniformly sampled
            self.data = data_dict['data']
            self.time = np.arange(len(self.data)) / 1000.0  # Assume 1 kHz
            self.sample_rate = 1000.0
            return True
        else:
            print("⚠️ Data format not recognised")
            return False
    
    def compute_spectrum(self):
        """Compute FFT of the data."""
        if self.data is None:
            return None
        
        # Remove mean and detrend
        detrended = self.data - np.mean(self.data)
        detrended = detrended - np.polyfit(np.arange(len(detrended)), detrended, 1)[1]
        
        # Window to reduce spectral leakage
        window = np.hanning(len(detrended))
        windowed = detrended * window
        
        # FFT
        n = len(windowed)
        spectrum = fft(windowed)
        frequencies = fftfreq(n, 1/self.sample_rate)
        
        # Only positive frequencies
        positive_idx = frequencies > 0
        self.frequencies = frequencies[positive_idx]
        self.spectrum = spectrum[positive_idx]
        
        return self.frequencies, self.spectrum
    
    def find_harmonic_comb(self, f_fundamental, tolerance=0.05):
        """
        Search for a 32-harmonic comb in the spectrum.
        
        Args:
            f_fundamental: Expected fundamental frequency (Hz)
            tolerance: Fractional tolerance for harmonic matching
        
        Returns:
            dict with detection results
        """
        if self.spectrum is None:
            self.compute_spectrum()
        
        if self.spectrum is None:
            return {'detected': [], 'confidence': 0.0}
        
        # Find peaks
        magnitude = np.abs(self.spectrum)
        peaks, properties = find_peaks(magnitude, height=np.percentile(magnitude, 95))
        
        detected_harmonics = []
        for k in range(1, N_HARMONICS + 1):
            expected_freq = k * f_fundamental
            # Search for peak within tolerance
            for peak in peaks:
                actual_freq = self.frequencies[peak]
                if abs(actual_freq - expected_freq) / expected_freq < tolerance:
                    detected_harmonics.append({
                        'k': k,
                        'frequency': actual_freq,
                        'amplitude': magnitude[peak],
                        'phase': np.angle(self.spectrum[peak])
                    })
                    break
        
        # Calculate confidence
        confidence = len(detected_harmonics) / N_HARMONICS
        
        # Extract phases
        phases = np.zeros(N_HARMONICS)
        amplitudes = np.zeros(N_HARMONICS)
        frequencies_found = np.zeros(N_HARMONICS)
        
        for h in detected_harmonics:
            k = h['k']
            phases[k-1] = h['phase']
            amplitudes[k-1] = h['amplitude']
            frequencies_found[k-1] = h['frequency']
        
        return {
            'detected': detected_harmonics,
            'confidence': confidence,
            'complete': confidence > 0.8,
            'phases': phases,
            'amplitudes': amplitudes,
            'frequencies': frequencies_found,
            'f_fundamental_measured': np.mean(frequencies_found[frequencies_found > 0]) if np.any(frequencies_found > 0) else f_fundamental
        }
    
    def extract_phase_relationships(self, detection_result):
        """
        Extract phase relationships from detected harmonics.
        """
        if not detection_result.get('complete', False):
            return None
        
        phases = detection_result['phases']
        amplitudes = detection_result['amplitudes']
        
        # Calculate phase differences from fundamental
        phase_diffs = phases - phases[0] if np.any(phases) else np.zeros(N_HARMONICS)
        
        # Normalise amplitudes
        if np.sum(amplitudes) > 0:
            amplitudes = amplitudes / np.sqrt(np.sum(amplitudes**2))
        
        # Calculate coherence
        ideal_phase = np.arange(N_HARMONICS) * PHI_0_RAD
        phase_error = np.mean(np.abs(phase_diffs - ideal_phase))
        coherence = np.exp(-phase_error * 10)
        
        return {
            'phase_diffs': phase_diffs,
            'amplitudes': amplitudes,
            'phase_error': phase_error,
            'coherence': coherence,
            'information': phase_diffs / (2.0 * np.pi / N_HARMONICS)
        }

# ============================================================================
# PHASE MEMORY MODEL (FOR RECONSTRUCTION)
# ============================================================================

class PhaseMemoryReader:
    """
    Reconstruct phase memory from detected signals.
    """
    
    def __init__(self):
        self.harmonics = np.arange(1, N_HARMONICS + 1)
        self.phase_signature = np.zeros(N_HARMONICS)
        
    def reconstruct_from_phases(self, phase_data, amplitude_data=None):
        """
        Reconstruct information from phase relationships.
        
        Args:
            phase_data: Array of phases (radians) for each harmonic
            amplitude_data: Array of amplitudes (optional)
        """
        if len(phase_data) != N_HARMONICS:
            phase_data = np.pad(phase_data, (0, N_HARMONICS - len(phase_data)))
        
        # Create memory model
        memory = PhaseMemory()
        memory.phases = phase_data
        if amplitude_data is not None and len(amplitude_data) == N_HARMONICS:
            memory.amplitudes = amplitude_data
        memory.coherence = self.calculate_coherence(phase_data)
        
        # Extract information
        info = self.extract_info(phase_data)
        
        return {
            'memory': memory,
            'information': info,
            'coherence': memory.coherence,
            'phase_data': phase_data,
            'amplitude_data': amplitude_data
        }
    
    def calculate_coherence(self, phases):
        """Calculate phase coherence."""
        total = 0.0
        pairs = 0
        for i in range(N_HARMONICS):
            for j in range(i + 1, N_HARMONICS):
                actual = abs(phases[i] - phases[j])
                ideal = 2.0 * np.pi * (j - i) / N_HARMONICS
                dev = actual - ideal
                total += np.exp(-dev**2 / (2.0 * np.pi**2))
                pairs += 1
        return total / pairs if pairs > 0 else 0.0
    
    def extract_info(self, phases):
        """Extract information from phase differences."""
        info = []
        for i in range(1, N_HARMONICS):
            phase_diff = phases[i] - phases[0]
            val = phase_diff / (2.0 * np.pi / N_HARMONICS)
            info.append(np.clip(val, 0.0, 1.0))
        return np.array(info)

# ============================================================================
# PHASE MEMORY MODEL (FOR SIMULATION)
# ============================================================================

class PhaseMemory:
    """
    Simple phase memory model for reconstruction.
    """
    
    def __init__(self):
        self.phases = np.zeros(N_HARMONICS)
        self.amplitudes = np.ones(N_HARMONICS) / np.sqrt(N_HARMONICS)
        self.coherence = 0.0

# ============================================================================
# BLACK HOLE PHYSICS
# ============================================================================

def black_hole_temperature(mass_solar):
    """Calculate Hawking temperature for a black hole."""
    M = mass_solar * M_SUN
    T_H = (H * C**3) / (8 * np.pi * G * M * K_B)
    return T_H

# ============================================================================
# MAIN GUI WITH REAL DATA SUPPORT
# ============================================================================

class BlackHolePhaseReaderGUI:
    """
    Interactive GUI for Black Hole Phase Memory Reader.
    Supports real data input from files.
    """
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.processor = SignalProcessor()
        self.reader = PhaseMemoryReader()
        self.current_data = None
        self.detection_result = None
        
        self.fig, self.axes = plt.subplots(2, 3, figsize=(15, 10))
        plt.subplots_adjust(bottom=0.40, left=0.08, right=0.95, top=0.92)
        
        self.setup_gui()
        self.update_display()
        
    def setup_gui(self):
        """Set up the GUI controls."""
        # Mass slider
        ax_mass = plt.axes([0.15, 0.30, 0.20, 0.03])
        self.mass_slider = Slider(
            ax_mass, 'Mass (M☉)', 1.0, 100.0,
            valinit=10.0, valstep=0.5
        )
        self.mass_slider.on_changed(self.update_display)
        
        # Data source selector
        ax_source = plt.axes([0.40, 0.30, 0.20, 0.03])
        self.source_text = TextBox(
            ax_source, 'Data Source',
            initial='simulated'
        )
        self.source_text.on_submit(self.load_data)
        
        # Load button
        ax_load = plt.axes([0.65, 0.30, 0.10, 0.04])
        self.load_btn = Button(ax_load, 'Load', color='lightblue', hovercolor='blue')
        self.load_btn.on_clicked(self.load_data)
        
        # Detect button
        ax_detect = plt.axes([0.45, 0.23, 0.15, 0.05])
        self.detect_btn = Button(ax_detect, 'Detect Harmonics', color='lightgreen', hovercolor='green')
        self.detect_btn.on_clicked(self.detect_harmonics)
        
        # Decode button
        ax_decode = plt.axes([0.65, 0.23, 0.15, 0.05])
        self.decode_btn = Button(ax_decode, 'Decode Info', color='orange', hovercolor='darkorange')
        self.decode_btn.on_clicked(self.decode_info)
        
        # Status display
        ax_status = plt.axes([0.15, 0.15, 0.65, 0.06])
        self.status_text = TextBox(
            ax_status, 'Status',
            initial='Ready. Load data or use simulation.',
            color='lightgray'
        )
        self.status_text.active = False
        
    def load_data(self, event=None):
        """Load data from source."""
        source = self.source_text.text.strip().lower()
        
        if source == 'simulated':
            mass = self.mass_slider.val
            self.current_data = self.data_loader.simulate_data(
                duration=10.0,
                sample_rate=1000.0,
                mass_solar=mass
            )
            self.status_text.set_val('✅ Loaded simulated data')
            
        elif source.startswith('file:'):
            filename = source[5:].strip()
            ext = os.path.splitext(filename)[1].lower()
            
            if ext == '.fits':
                self.current_data = self.data_loader.load_fits(filename)
            elif ext == '.csv':
                self.current_data = self.data_loader.load_csv(filename)
            elif ext == '.npy':
                self.current_data = self.data_loader.load_npy(filename)
            elif ext == '.json':
                self.current_data = self.data_loader.load_json(filename)
            else:
                self.status_text.set_val(f'⚠️ Unknown file type: {ext}')
                return
            
            if self.current_data is not None:
                self.status_text.set_val(f'✅ Loaded {filename}')
            else:
                self.status_text.set_val('❌ Failed to load file')
                return
        
        else:
            # Try to interpret as a file path
            if os.path.exists(source):
                ext = os.path.splitext(source)[1].lower()
                if ext == '.fits':
                    self.current_data = self.data_loader.load_fits(source)
                elif ext == '.csv':
                    self.current_data = self.data_loader.load_csv(source)
                elif ext == '.npy':
                    self.current_data = self.data_loader.load_npy(source)
                else:
                    self.status_text.set_val(f'⚠️ Unknown file type: {ext}')
                    return
                
                if self.current_data is not None:
                    self.status_text.set_val(f'✅ Loaded {source}')
                else:
                    self.status_text.set_val('❌ Failed to load file')
                    return
            else:
                self.status_text.set_val(f'⚠️ Source not found: {source}')
                return
        
        # Process the data
        if self.current_data is not None:
            self.processor.load_data(self.current_data)
            self.processor.compute_spectrum()
            self.status_text.set_val(f'✅ Data loaded and processed')
            self.update_display()
        
    def detect_harmonics(self, event=None):
        """Detect harmonic comb in data."""
        if self.current_data is None:
            self.status_text.set_val('⚠️ No data loaded. Load data first.')
            return
        
        mass = self.mass_slider.val
        f_fundamental = K_B * black_hole_temperature(mass) / H
        
        self.detection_result = self.processor.find_harmonic_comb(f_fundamental)
        
        if self.detection_result['complete']:
            self.status_text.set_val(
                f'✅ Detected {len(self.detection_result["detected"])}/32 harmonics. '
                f'Confidence: {self.detection_result["confidence"]:.2%}'
            )
        else:
            self.status_text.set_val(
                f'⚠️ Detected {len(self.detection_result["detected"])}/32 harmonics. '
                f'Confidence: {self.detection_result["confidence"]:.2%}'
            )
        
        self.update_display()
        
    def decode_info(self, event=None):
        """Decode information from detected harmonics."""
        if self.detection_result is None or not self.detection_result['complete']:
            self.status_text.set_val('⚠️ No reliable harmonic detection. Detect first.')
            return
        
        phase_data = self.detection_result['phases']
        amplitude_data = self.detection_result['amplitudes']
        
        decoded = self.reader.reconstruct_from_phases(phase_data, amplitude_data)
        
        # Convert to approximate text
        info = decoded['information']
        text = ''
        for val in info[:20]:
            char_code = int(val * 26) + 65
            if 65 <= char_code <= 90:
                text += chr(char_code)
        
        self.status_text.set_val(
            f'📖 Decoded: {len(info)} bits | Coherence: {decoded["coherence"]:.4f} | '
            f'Text (approx): {text[:15]}'
        )
        
        self.update_display()
        
    def update_display(self, val=None):
        """Update all displays."""
        mass = self.mass_slider.val
        
        # Plot 1: Raw data
        ax1 = self.axes[0, 0]
        ax1.clear()
        if self.processor.data is not None:
            ax1.plot(self.processor.time[:5000], self.processor.data[:5000])
            ax1.set_title('Raw Data (First 5s)')
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Amplitude')
        else:
            ax1.text(0.5, 0.5, 'No data loaded', ha='center', va='center')
        ax1.grid(True, alpha=0.3)
        
        # Plot 2: Spectrum
        ax2 = self.axes[0, 1]
        ax2.clear()
        if self.processor.spectrum is not None:
            ax2.loglog(self.processor.frequencies[1:], np.abs(self.processor.spectrum[1:]))
            ax2.set_title('Power Spectrum')
            ax2.set_xlabel('Frequency (Hz)')
            ax2.set_ylabel('Magnitude')
            
            # Mark harmonic comb if detected
            if self.detection_result is not None:
                for h in self.detection_result['detected']:
                    ax2.axvline(h['frequency'], color='r', alpha=0.5, linestyle='--')
        else:
            ax2.text(0.5, 0.5, 'No spectrum', ha='center', va='center')
        ax2.grid(True, alpha=0.3)
        
        # Plot 3: Harmonic detection
        ax3 = self.axes[0, 2]
        ax3.clear()
        if self.detection_result is not None:
            detected = [h['k'] for h in self.detection_result['detected']]
            amplitudes = [h['amplitude'] for h in self.detection_result['detected']]
            ax3.bar(detected, amplitudes, color='blue', alpha=0.7)
            ax3.set_title(f'Harmonic Detection ({len(detected)}/32)')
            ax3.set_xlabel('Harmonic k')
            ax3.set_ylabel('Amplitude')
            ax3.set_xticks(range(1, 33, 4))
        else:
            ax3.text(0.5, 0.5, 'No detection', ha='center', va='center')
        ax3.grid(True, alpha=0.3)
        
        # Plot 4: Phase relationships
        ax4 = self.axes[1, 0]
        ax4.clear()
        if self.detection_result is not None and self.detection_result['complete']:
            phases = self.detection_result['phases']
            ax4.plot(range(1, N_HARMONICS+1), np.degrees(phases), 'bo-')
            ax4.set_title('Phase Relationships')
            ax4.set_xlabel('Harmonic k')
            ax4.set_ylabel('Phase (degrees)')
            ax4.set_xticks(range(1, 33, 4))
        else:
            ax4.text(0.5, 0.5, 'No phase data', ha='center', va='center')
        ax4.grid(True, alpha=0.3)
        
        # Plot 5: Information
        ax5 = self.axes[1, 1]
        ax5.clear()
        if self.detection_result is not None and self.detection_result['complete']:
            decoded = self.reader.reconstruct_from_phases(
                self.detection_result['phases'],
                self.detection_result['amplitudes']
            )
            info = decoded['information'][:20]
            ax5.bar(range(len(info)), info, color='green', alpha=0.7)
            ax5.set_title(f'Extracted Information ({len(info)} bits)')
            ax5.set_xlabel('Bit Index')
            ax5.set_ylabel('Value')
        else:
            ax5.text(0.5, 0.5, 'No information', ha='center', va='center')
        ax5.grid(True, alpha=0.3)
        
        # Plot 6: Coherence and status
        ax6 = self.axes[1, 2]
        ax6.clear()
        if self.detection_result is not None:
            coherence = self.detection_result['confidence']
            ax6.bar(['Coherence'], [coherence], color='green' if coherence > 0.8 else 'orange')
            ax6.set_ylim(0, 1)
            ax6.set_title(f'Detection Confidence\n{coherence:.2%}')
        else:
            ax6.text(0.5, 0.5, 'No detection', ha='center', va='center')
        ax6.grid(True, alpha=0.3)
        
        # Update info text
        status = self.status_text.text if hasattr(self.status_text, 'text') else 'Ready'
        self.fig.suptitle(
            f'Black Hole Phase Memory Reader v2.0\n'
            f'Mass: {mass:.1f} M☉, T_H: {black_hole_temperature(mass):.2e} K | {status}',
            fontsize=11
        )
        
        plt.draw()

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    print("=" * 80)
    print("BLACK HOLE PHASE MEMORY READER v2.0")
    print("Harmonic Framework Implementation")
    print("Paper 30: The Black Hole Information Paradox as Phase Memory")
    print("=" * 80)
    print()
    print("This program can read:")
    print("  • Simulated data (default)")
    print("  • FITS files (radio telescopes, X-ray)")
    print("  • CSV files (time, amplitude)")
    print("  • NPY files (NumPy arrays)")
    print("  • JSON files (spectral data)")
    print()
    print("To load data: Type 'file:filename' in the Data Source box")
    print("Example: file:data.fits")
    print("Example: file:spectrum.csv")
    print()
    print("Starting GUI...")
    print()
    
    gui = BlackHolePhaseReaderGUI()
    plt.show()
    
    print()
    print("=" * 80)
    print("PROGRAM COMPLETE")
    print("The information is not destroyed. It is phase-shifted.")
    print("=" * 80)

if __name__ == "__main__":
    main()