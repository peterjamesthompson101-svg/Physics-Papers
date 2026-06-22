#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Harmonic Grand Unified Theory (GUT) - Complete Simulator v2.0

Updated to reflect corrected theory:
- T1 (Matter): n = ln(P)/ln(27) continuous spectrum
- T2 (Antimatter): No n. Defined by f_c2 = anchor/230 and m_anti = h*f_c2/c^2 * k
- T3 (Dark Matter): No n. Defined by f_c3 = anchor*(13/19)/230 and m_dm = h*f_c3/c^2 * k

Author: Peter James Thompson
Date: June 2026
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.colors import LogNorm
import pandas as pd

# ============================================================================
# PHYSICAL CONSTANTS
# ============================================================================

H = 6.626e-34          # Planck constant (J·s)
C = 3e8                # Speed of light (m/s)
M_NUCLEON = 1.67e-27   # Nucleon mass (kg) - approximate for mass number A

# ============================================================================
# HARMONIC MAGIC NUMBERS (Proton/Neutron shell closures)
# ============================================================================

MAGIC_NUMBERS = np.array([2, 8, 20, 28, 50, 82, 126, 184, 258, 318, 400])

# ============================================================================
# FREQUENCY TO MASS CONVERSION
# ============================================================================

def freq_to_mass(freq_hz):
    """Convert frequency to mass in kg via E = h*f."""
    return H * freq_hz / (C * C)

def freq_to_ev(freq_hz):
    """Convert frequency to mass in eV."""
    mass_kg = freq_to_mass(freq_hz)
    return mass_kg * C * C / 1.602e-19

def mass_to_freq(mass_kg):
    """Convert mass to frequency via E = h*f."""
    return mass_kg * C * C / H

# ============================================================================
# COHERENCE SCORE - Complete Implementation
# ============================================================================

def coherence_score(Z, N, anchor_hz, ratio_19_13, cutoff_hz, exponent_n, branch_mix, t3_coupling):
    """
    Compute harmonic coherence for a nucleus (Z,N) based on GUT parameters.

    branch_mix:
        +1   = pure matter branch (T1, forward time, positive n)
        -1   = pure antimatter branch (T2, reverse time, no n)
        0    = pure T3 (dark matter branch, orthogonal time, no n)
        between = mixed regime (T3 coupling matters)

    t3_coupling: 0.0 to 1.0 - how much T3 admixture (dark matter component)

    Returns coherence in [0,1].
    """
    A = Z + N  # mass number

    # ------------------------------------------------------------------------
    # Common terms (used in all branches)
    # ------------------------------------------------------------------------

    # 1) Resonance term: product of scaled frequencies aligns with integer multiples of anchor
    f_scale = A * anchor_hz / 27.0
    resonance = np.exp(-5.0 * np.abs(f_scale - np.round(f_scale)))

    # 2) Magic number proximity (normalised)
    Z_magic_dist = np.min(np.abs(Z - MAGIC_NUMBERS)) / 40.0
    N_magic_dist = np.min(np.abs(N - MAGIC_NUMBERS)) / 40.0

    # 3) 19:13 ratio penalty (ideal Z/N)
    if N > 0:
        ratio = Z / N
        ratio_penalty = np.abs(ratio - ratio_19_13) / ratio_19_13
    else:
        ratio_penalty = 1.0

    # ------------------------------------------------------------------------
    # Branch-specific calculations
    # ------------------------------------------------------------------------

    if branch_mix >= 0.5:
        # ============================================================
        # T1: MATTER BRANCH (forward time, positive n)
        # n = ln(P)/ln(27) continuous spectrum
        # ============================================================

        # 4a) Dimensional exponent resonance
        n_val = np.log(A + 1.0) / np.log(anchor_hz) if anchor_hz > 1 else 0.0
        n_target = exponent_n
        n_res = np.exp(-2.0 * np.abs(np.sin(np.pi * (n_val - n_target))))

        # 5a) 230th subharmonic penalty
        n_eff = A / 230.0
        n_penalty = np.exp(-10.0 * np.abs(n_eff - np.round(n_eff)))

        # Combine all terms
        coherence = resonance * n_penalty * n_res * np.exp(-(Z_magic_dist + N_magic_dist + ratio_penalty))

    elif branch_mix <= -0.5:
        # ============================================================
        # T2: ANTIMATTER BRANCH (reverse time, NO n)
        # Defined by f_c2 = anchor/230, mass ladder m_anti = h*f_c2/c^2 * k
        # ============================================================

        # 4b) Antimatter cutoff frequency
        f_c2 = anchor_hz / 230.0

        # 5b) Mass ladder resonance:
        # The nucleus mass (A * m_nucleon) should correspond to k * (h*f_c2/c^2)
        m_c2 = freq_to_mass(f_c2)
        k = A * M_NUCLEON / m_c2
        k_round = np.round(k)
        ladder_resonance = np.exp(-5.0 * np.abs(k - k_round))

        # 6b) 230th subharmonic (T2 boundary)
        n_eff = A / 230.0
        n_penalty = np.exp(-10.0 * np.abs(n_eff - np.round(n_eff)))

        # Combine all terms
        coherence = ladder_resonance * n_penalty * np.exp(-(Z_magic_dist + N_magic_dist + ratio_penalty))

    else:
        # ============================================================
        # T3: DARK MATTER BRANCH (orthogonal time, NO n)
        # Defined by f_c3 = anchor*(13/19)/230, mass ladder m_dm = h*f_c3/c^2 * k
        # ============================================================

        # 4c) Dark matter cutoff frequency
        f_c3 = anchor_hz * (13.0 / 19.0) / 230.0

        # 5c) Mass ladder resonance:
        m_c3 = freq_to_mass(f_c3)
        k = A * M_NUCLEON / m_c3
        k_round = np.round(k)
        ladder_resonance = np.exp(-5.0 * np.abs(k - k_round))

        # 6c) T3-specific penalty (using f_c3 instead of f_c2)
        n_eff_T3 = A * (13.0 / 19.0) / 230.0
        n_penalty = np.exp(-10.0 * np.abs(n_eff_T3 - np.round(n_eff_T3)))

        # 7c) Base coherence
        coherence = ladder_resonance * n_penalty * np.exp(-(Z_magic_dist + N_magic_dist + ratio_penalty))

        # 8c) Apply T3 coupling (if in mixed regime)
        if t3_coupling > 0:
            coherence = coherence * (1.0 - t3_coupling) + t3_coupling * 0.8

    # Clip to valid range
    return np.clip(coherence, 0.0, 1.0)

# ============================================================================
# HALF-LIFE CALIBRATION
# ============================================================================

def half_life_from_coherence(coh, ref_coh=0.45, ref_hl=0.08, beta=8.0):
    """
    Estimate half-life from coherence score.
    Calibrated to Tennessine-294: Z=117, N=177, coherence ~0.45, half-life 0.08 s.
    """
    safe_coh = max(1e-6, min(0.999999, coh))
    log_hl = np.log(ref_hl) + beta * (safe_coh - ref_coh) / (1.0 - safe_coh + 1e-6)
    return np.exp(log_hl)

# ============================================================================
# QUANTUM HANDSHAKE CLASSES
# ============================================================================

class QuantumHandshakeT1T2:
    """Handshake between matter (T1) and antimatter (T2) at 230th subharmonic."""
    def __init__(self, freq_hz=0.1174, phase_offset_deg=-1.0):
        self.carrier_freq = freq_hz
        self.phase_offset = np.radians(phase_offset_deg)
        self.t1_phase = 0.0
        self.locked = False
        self.energy_extracted = 0.0

    def update(self, dt, t2_feedback_phase, coupling=0.5):
        error = (t2_feedback_phase - self.t1_phase - self.phase_offset) % (2 * np.pi)
        if error > np.pi:
            error -= 2 * np.pi
        self.t1_phase += coupling * error * dt
        self.locked = abs(error) < 0.01
        if self.locked:
            energy = 10000.0 * max(0.0, t2_feedback_phase) * dt
            self.energy_extracted += energy
        return self.t1_phase


class QuantumHandshakeT1T3:
    """Handshake between matter (T1) and dark matter (T3) at dark resonance frequency."""
    def __init__(self, freq_hz=0.08032, phase_offset_deg=-1.0):
        self.carrier_freq = freq_hz
        self.phase_offset = np.radians(phase_offset_deg)
        self.t1_phase = 0.0
        self.locked = False
        self.energy_extracted = 0.0

    def update(self, dt, t3_feedback_phase, coupling=0.3):
        error = (t3_feedback_phase - self.t1_phase - self.phase_offset) % (2 * np.pi)
        if error > np.pi:
            error -= 2 * np.pi
        self.t1_phase += coupling * error * dt
        self.locked = abs(error) < 0.01
        if self.locked:
            energy = 1000.0 * max(0.0, t3_feedback_phase) * dt  # lower coupling
            self.energy_extracted += energy
        return self.t1_phase

# ============================================================================
# ELEMENT NAME GENERATOR (for extended anti-element table)
# ============================================================================

def element_name(Z):
    if Z <= 118:
        return f"Element {int(Z)}"
    digits = ['nil', 'un', 'bi', 'tri', 'quad', 'pent', 'hex', 'sept', 'oct', 'enn']
    name = ''.join(digits[int(d)] for d in str(int(Z))) + 'ium'
    return name.capitalize()

# ============================================================================
# GRID DEFINITION
# ============================================================================

Z_vals = np.arange(100, 185, 2, dtype=np.float64)
N_vals = np.arange(140, 401, 2, dtype=np.float64)
extent = [N_vals[0], N_vals[-1], Z_vals[0], Z_vals[-1]]

# ============================================================================
# DEFAULT PARAMETERS
# ============================================================================

anchor_default = 27.0
ratio_default = 19.0 / 13.0
cutoff_default = anchor_default / 230.0
n_default = 3.54
branch_default = 1.0  # matter branch
t3_default = 0.0

# ============================================================================
# INITIAL COHERENCE MAP (Matter branch)
# ============================================================================

coherence_init = np.zeros((len(Z_vals), len(N_vals)))
for i, Z in enumerate(Z_vals):
    for j, N in enumerate(N_vals):
        coherence_init[i, j] = coherence_score(Z, N, anchor_default, ratio_default,
                                               cutoff_default, n_default, branch_default, t3_default)

# ============================================================================
# CREATE MAIN INTERACTIVE FIGURE
# ============================================================================

fig, ax = plt.subplots(figsize=(12, 8))
plt.subplots_adjust(bottom=0.45, left=0.1)

im = ax.imshow(coherence_init, origin='lower', aspect='auto', cmap='hot_r',
               extent=extent, norm=LogNorm(vmin=0.001, vmax=1))
cbar = plt.colorbar(im, ax=ax, label='Harmonic Coherence (higher = more stable)')

# Mark magic numbers
for m in MAGIC_NUMBERS:
    if m >= Z_vals.min() and m <= Z_vals.max():
        ax.axhline(y=m, color='cyan', linestyle='--', linewidth=0.8, alpha=0.6)
    if m >= N_vals.min() and m <= N_vals.max():
        ax.axvline(x=m, color='cyan', linestyle='--', linewidth=0.8, alpha=0.6)

# Highlight predicted islands (matter side)
ax.scatter([184], [126], color='lime', s=100, marker='*', label='Island: Z=126,N=184')
ax.scatter([184], [120], color='yellow', s=80, marker='*', label='Z=120,N=184')
ax.scatter([196], [126], color='cyan', s=80, marker='s', label='Z=126,N=196')
ax.scatter([318], [164], color='orange', s=100, marker='D', label='Z=164,N=318')
ax.legend(loc='upper left')

ax.set_xlabel('Neutron Number (N)')
ax.set_ylabel('Proton Number (Z)')
ax.grid(alpha=0.3)

ax.set_title(f'Harmonic Framework - Stability Islands (Matter Branch)\n'
             f'Anchor = {anchor_default} Hz, Ratio = {ratio_default:.4f}, '
             f'Cutoff = {cutoff_default:.4f} Hz, n = {n_default}', fontsize=14)

# ============================================================================
# SLIDERS
# ============================================================================

ax_freq = plt.axes([0.2, 0.38, 0.6, 0.03])
freq_slider = Slider(ax_freq, 'Anchor Freq (Hz)', 20.0, 34.0,
                     valinit=anchor_default, valstep=0.1)

ax_ratio = plt.axes([0.2, 0.32, 0.6, 0.03])
ratio_slider = Slider(ax_ratio, '19:13 Ratio', 1.30, 1.60,
                      valinit=ratio_default, valstep=0.001)

ax_cutoff = plt.axes([0.2, 0.26, 0.6, 0.03])
cutoff_slider = Slider(ax_cutoff, '230th Cutoff (Hz)', 0.05, 0.30,
                       valinit=cutoff_default, valstep=0.001)

ax_n = plt.axes([0.2, 0.20, 0.6, 0.03])
n_slider = Slider(ax_n, 'Exponent n (T1 only)', 0.0, 10.0,
                  valinit=n_default, valstep=0.01)

ax_branch = plt.axes([0.2, 0.14, 0.6, 0.03])
branch_slider = Slider(ax_branch, 'Branch (+1=matter, -1=anti, 0=T3 dark)',
                       -1.0, 1.0, valinit=branch_default, valstep=0.01)

ax_t3 = plt.axes([0.2, 0.08, 0.6, 0.03])
t3_slider = Slider(ax_t3, 'T3 Dark Coupling (0..1)', 0.0, 1.0,
                   valinit=t3_default, valstep=0.01)

# ============================================================================
# UPDATE FUNCTION
# ============================================================================

def update(val):
    anchor = freq_slider.val
    ratio = ratio_slider.val
    cutoff = cutoff_slider.val
    n_exp = n_slider.val
    branch = branch_slider.val
    t3 = t3_slider.val

    new_coh = np.zeros((len(Z_vals), len(N_vals)))
    for i, Z in enumerate(Z_vals):
        for j, N in enumerate(N_vals):
            new_coh[i, j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, branch, t3)

    im.set_data(new_coh)

    if branch > 0.5:
        mode = "Matter Branch (T1, forward time) – n = ln(P)/ln(27)"
    elif branch < -0.5:
        mode = "Anti-Element Branch (T2, reverse time) – no n, f_c2 = anchor/230"
    else:
        mode = f"Dark Matter Branch (T3, orthogonal time) – no n, f_c3 = anchor*(13/19)/230, coupling={t3:.2f}"

    ax.set_title(f'Harmonic Framework - {mode}\n'
                 f'Anchor={anchor:.1f} Hz, Ratio={ratio:.4f}, '
                 f'Cutoff={cutoff:.4f} Hz, n={n_exp:.2f}', fontsize=14)
    fig.canvas.draw_idle()

freq_slider.on_changed(update)
ratio_slider.on_changed(update)
cutoff_slider.on_changed(update)
n_slider.on_changed(update)
branch_slider.on_changed(update)
t3_slider.on_changed(update)

# ============================================================================
# GREEN MARKERS FOR DEFAULT VALUES
# ============================================================================

def add_green_marker(slider, value, label):
    asl = slider.ax
    vmin, vmax = slider.valmin, slider.valmax
    norm = (value - vmin) / (vmax - vmin)
    asl.axvline(x=norm, ymin=0, ymax=1, color='green', linewidth=2, alpha=0.7)
    asl.text(norm, -0.6, label, transform=asl.transAxes, ha='center', va='top', color='green')

add_green_marker(freq_slider, anchor_default, '27 Hz')
add_green_marker(ratio_slider, ratio_default, '19/13')
add_green_marker(cutoff_slider, cutoff_default, f'{cutoff_default:.3f} Hz')
add_green_marker(n_slider, n_default, f'n={n_default}')
add_green_marker(branch_slider, branch_default, 'Matter (+1)')
add_green_marker(t3_slider, t3_default, 'T3=0')

# ============================================================================
# BUTTON: SIDE-BY-SIDE COMPARISON (T1, T2, T3)
# ============================================================================

ax_compare = plt.axes([0.05, 0.02, 0.18, 0.04])
compare_btn = Button(ax_compare, 'Compare T1/T2/T3', color='lightgray', hovercolor='yellow')

def show_comparison(event):
    anchor = freq_slider.val
    ratio = ratio_slider.val
    cutoff = cutoff_slider.val
    n_exp = n_slider.val
    t3 = t3_slider.val

    # T1 (matter)
    matter = np.zeros((len(Z_vals), len(N_vals)))
    for i, Z in enumerate(Z_vals):
        for j, N in enumerate(N_vals):
            matter[i, j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, 1.0, t3)

    # T2 (antimatter)
    anti = np.zeros((len(Z_vals), len(N_vals)))
    for i, Z in enumerate(Z_vals):
        for j, N in enumerate(N_vals):
            anti[i, j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, -1.0, t3)

    # T3 (dark matter)
    dark = np.zeros((len(Z_vals), len(N_vals)))
    for i, Z in enumerate(Z_vals):
        for j, N in enumerate(N_vals):
            dark[i, j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, 0.0, t3)

    fig2, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    fig2.suptitle(f'Three Branches: Matter (T1) | Anti-Matter (T2) | Dark Matter (T3)\n'
                  f'Anchor={anchor:.1f} Hz, Ratio={ratio:.4f}, '
                  f'Cutoff={cutoff:.4f} Hz, n={n_exp:.2f}', fontsize=12)

    im1 = ax1.imshow(matter, origin='lower', aspect='auto', cmap='hot_r',
                     extent=extent, norm=LogNorm(vmin=0.001, vmax=1))
    ax1.set_title('Matter Branch (T1) – n continuous')
    ax1.set_xlabel('Neutron Number N')
    ax1.set_ylabel('Proton Number Z')
    plt.colorbar(im1, ax=ax1, label='Coherence')

    im2 = ax2.imshow(anti, origin='lower', aspect='auto', cmap='hot_r',
                     extent=extent, norm=LogNorm(vmin=0.001, vmax=1))
    ax2.set_title('Anti-Matter Branch (T2) – f_c2 = anchor/230')
    ax2.set_xlabel('Neutron Number N')
    plt.colorbar(im2, ax=ax2, label='Coherence')

    im3 = ax3.imshow(dark, origin='lower', aspect='auto', cmap='hot_r',
                     extent=extent, norm=LogNorm(vmin=0.001, vmax=1))
    ax3.set_title('Dark Matter Branch (T3) – f_c3 = anchor*(13/19)/230')
    ax3.set_xlabel('Neutron Number N')
    plt.colorbar(im3, ax=ax3, label='Coherence')

    # Mark magic numbers on all three
    for axs in (ax1, ax2, ax3):
        for m in MAGIC_NUMBERS:
            if m >= Z_vals.min() and m <= Z_vals.max():
                axs.axhline(y=m, color='cyan', linestyle='--', alpha=0.6)
            if m >= N_vals.min() and m <= N_vals.max():
                axs.axvline(x=m, color='cyan', linestyle='--', alpha=0.6)

    plt.tight_layout()
    plt.show()

compare_btn.on_clicked(show_comparison)

# ============================================================================
# BUTTON: EXTENDED ANTI-ELEMENT TABLE (AND DARK MASS SPECTRUM)
# ============================================================================

ax_table = plt.axes([0.26, 0.02, 0.18, 0.04])
table_btn = Button(ax_table, 'Extended Table', color='lightgray', hovercolor='yellow')

def show_extended_table(event):
    anchor = freq_slider.val
    ratio = ratio_slider.val
    cutoff = cutoff_slider.val
    n_exp = n_slider.val

    # Anti-branch (T2) – compute coherence using corrected T2 logic
    anti_coh = np.zeros((len(Z_vals), len(N_vals)))
    for i, Z in enumerate(Z_vals):
        for j, N in enumerate(N_vals):
            anti_coh[i, j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, -1.0, 0.0)

    # Find local maxima with coherence > 0.7
    peaks = []
    for i in range(1, len(Z_vals) - 1):
        for j in range(1, len(N_vals) - 1):
            c = anti_coh[i, j]
            if c > 0.7 and c >= anti_coh[i-1, j] and c >= anti_coh[i+1, j] \
               and c >= anti_coh[i, j-1] and c >= anti_coh[i, j+1]:
                Z = Z_vals[i]
                N = N_vals[j]
                hl = half_life_from_coherence(c)
                peaks.append((Z, N, c, hl))

    peaks.sort(key=lambda x: x[2], reverse=True)

    print("\n" + "=" * 80)
    print("Extended Anti-Element Table (T2 Reverse Time Branch) – f_c2 = anchor/230")
    print("=" * 80)
    print(f"{'Z':<5} {'N':<6} {'Element Name':<25} {'Coherence':<10} {'Half-Life (sec)':<15} {'Approx':<15}")
    print("-" * 80)

    for Z, N, coh, hl in peaks[:20]:
        name = element_name(Z)
        if hl < 60:
            hl_str = f"{hl:.2f} s"
        elif hl < 86400:
            hl_str = f"{hl/60:.1f} min"
        else:
            hl_str = f"{hl/86400:.1f} days"
        print(f"{int(Z):<5} {int(N):<6} {name:<25} {coh:.4f} {hl:.2e} {hl_str}")

    # Dark matter mass spectrum (T3 branch)
    print("\n" + "=" * 80)
    print("Dark Matter (T3 Branch) – f_c3 = anchor * (13/19) / 230")
    print("=" * 80)

    f_c3 = anchor * (13.0 / 19.0) / 230.0
    print(f"T3 cutoff frequency: {f_c3:.5f} Hz – mass ~ {freq_to_ev(f_c3):.2e} eV")

    for k in range(1, 10):
        f = k * f_c3
        m_ev = freq_to_ev(f)
        mass_kg = freq_to_mass(f)
        print(f"  Harmonic {k}: {f:.5f} Hz – {m_ev:.2e} eV – {mass_kg:.2e} kg")

    # Save to CSV
    df = pd.DataFrame(peaks, columns=['Z', 'N', 'Coherence', 'HalfLife_sec'])
    df['ElementName'] = df['Z'].apply(element_name)
    df.to_csv('anti_element_extended.csv', index=False)
    print("\nTable saved to 'anti_element_extended.csv'")

table_btn.on_clicked(show_extended_table)

# ============================================================================
# BUTTON: QUANTUM HANDSHAKE T1–T2
# ============================================================================

ax_hs12 = plt.axes([0.48, 0.02, 0.18, 0.04])
hs12_btn = Button(ax_hs12, 'Handshake T1–T2', color='lightgray', hovercolor='yellow')

def run_handshake_t1t2(event):
    anchor = freq_slider.val
    f_c2 = anchor / 230.0

    fig_hs, ax_hs = plt.subplots(figsize=(8, 5))
    plt.subplots_adjust(bottom=0.2)

    ax_hs.set_xlim(0, 20)
    ax_hs.set_ylim(0, 1.2)
    ax_hs.set_xlabel('Time (s)')
    ax_hs.set_ylabel('Energy Extracted / Lock Status')
    ax_hs.set_title(f'Quantum Handshake T1–T2 (230th subharmonic)\n'
                    f'f_c2 = {f_c2:.5f} Hz\n'
                    f'Energy Harvesting from Anti-Matter Branch')

    line_energy, = ax_hs.plot([], [], 'b-', label='Harvested Energy (scaled)')
    line_lock, = ax_hs.plot([], [], 'g--', label='Locked (1=yes)')
    ax_hs.legend(loc='upper left')

    hs = QuantumHandshakeT1T2(freq_hz=f_c2, phase_offset_deg=-1.0)
    t = np.linspace(0, 20, 2000)
    dt = t[1] - t[0]
    energy_log = []
    lock_log = []

    t2_phase = 0.0
    for ti in t:
        t2_phase = 0.5 * np.sin(2 * np.pi * 0.5 * ti) + 0.2 * ti
        hs.update(dt, t2_phase, coupling=0.5)
        energy_log.append(hs.energy_extracted)
        lock_log.append(1.0 if hs.locked else 0.0)

    line_energy.set_data(t, energy_log)
    line_lock.set_data(t, lock_log)
    ax_hs.relim()
    ax_hs.autoscale_view()
    plt.show()

hs12_btn.on_clicked(run_handshake_t1t2)

# ============================================================================
# BUTTON: QUANTUM HANDSHAKE T1–T3
# ============================================================================

ax_hs13 = plt.axes([0.70, 0.02, 0.18, 0.04])
hs13_btn = Button(ax_hs13, 'Handshake T1–T3', color='lightgray', hovercolor='yellow')

def run_handshake_t1t3(event):
    anchor = freq_slider.val
    f_c3 = anchor * (13.0 / 19.0) / 230.0

    fig_hs, ax_hs = plt.subplots(figsize=(8, 5))
    plt.subplots_adjust(bottom=0.2)

    ax_hs.set_xlim(0, 20)
    ax_hs.set_ylim(0, 1.2)
    ax_hs.set_xlabel('Time (s)')
    ax_hs.set_ylabel('Energy Extracted / Lock Status')
    ax_hs.set_title(f'Quantum Handshake T1–T3 (Dark Resonance)\n'
                    f'f_c3 = {f_c3:.5f} Hz\n'
                    f'Energy Harvesting from Dark Matter Background')

    line_energy, = ax_hs.plot([], [], 'b-', label='Harvested Energy (scaled)')
    line_lock, = ax_hs.plot([], [], 'g--', label='Locked (1=yes)')
    ax_hs.legend(loc='upper left')

    hs = QuantumHandshakeT1T3(freq_hz=f_c3, phase_offset_deg=-1.0)
    t = np.linspace(0, 20, 2000)
    dt = t[1] - t[0]
    energy_log = []
    lock_log = []

    t3_phase = 0.0
    for ti in t:
        t3_phase = 0.3 * np.sin(2 * np.pi * 0.3 * ti) + 0.1 * ti
        hs.update(dt, t3_phase, coupling=0.3)
        energy_log.append(hs.energy_extracted)
        lock_log.append(1.0 if hs.locked else 0.0)

    line_energy.set_data(t, energy_log)
    line_lock.set_data(t, lock_log)
    ax_hs.relim()
    ax_hs.autoscale_view()
    plt.show()

hs13_btn.on_clicked(run_handshake_t1t3)

# ============================================================================
# LAUNCH INTERACTIVE WINDOW
# ============================================================================

plt.show()

print("\n" + "=" * 80)
print("GUT SIMULATOR v2.0 - COMPLETE")
print("=" * 80)
print("Branches:")
print("  T1 (Matter):       n = ln(P)/ln(27) – continuous spectrum")
print("  T2 (Antimatter):   f_c2 = anchor/230 – no n, mass ladder")
print("  T3 (Dark Matter):  f_c3 = anchor*(13/19)/230 – no n, mass ladder")
print("=" * 80)