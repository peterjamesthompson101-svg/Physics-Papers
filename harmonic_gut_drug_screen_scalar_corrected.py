#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harmonic Grand Unified Theory (GUT) – Complete Simulator
with Drug Screening, Scalar Wave Integration (corrected S_dir = 1/9)
Author: Peter James Thompson, June 2026
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.colors import LogNorm
import pandas as pd
import os
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# =============================================================================
# HARMONIC CONSTANTS
# =============================================================================
MAGIC_NUMBERS = np.array([2, 8, 20, 28, 50, 82, 126, 184, 258, 318, 400])
ANCHOR_DEFAULT = 27.0
RATIO_DEFAULT = 19.0 / 13.0
CUTOFF_DEFAULT = ANCHOR_DEFAULT / 230.0
N_DEFAULT = 3.54
BRANCH_DEFAULT = 1.0
T3_DEFAULT = 0.0

# -------------------------------------------------------------------------
# CORE COHERENCE FUNCTION (for nuclei) – unchanged
# -------------------------------------------------------------------------
def coherence_score(Z, N, anchor_hz, ratio_19_13, cutoff_hz, exponent_n, branch_mix, t3_coupling):
    A = Z + N
    f_scale = A * anchor_hz / 27.0
    resonance = np.exp(-5.0 * np.abs(f_scale - np.round(f_scale)))
    Z_magic_dist = np.min(np.abs(Z - MAGIC_NUMBERS)) / 40.0
    N_magic_dist = np.min(np.abs(N - MAGIC_NUMBERS)) / 40.0
    if N > 0:
        ratio = Z / N
        ratio_penalty = np.abs(ratio - ratio_19_13) / ratio_19_13
    else:
        ratio_penalty = 1.0
    n_eff = A / 230.0
    n_penalty = np.exp(-10.0 * np.abs(n_eff - np.round(n_eff)))
    n_val = np.log(A + 1.0) / np.log(anchor_hz) if anchor_hz > 1 else 0.0
    if branch_mix >= 0.5:
        n_target = exponent_n
        n_res = np.exp(-2.0 * np.abs(np.sin(np.pi * (n_val - n_target))))
    elif branch_mix <= -0.5:
        n_target = -exponent_n
        n_res = np.exp(-2.0 * np.abs(np.sin(np.pi * (n_val - n_target))))
    else:
        n_target_T3 = exponent_n * (13.0 / 19.0)
        n_res = np.exp(-2.0 * np.abs(np.sin(np.pi * (n_val - n_target_T3))))
        n_eff_T3 = A * (13.0/19.0) / 230.0
        n_penalty = np.exp(-10.0 * np.abs(n_eff_T3 - np.round(n_eff_T3)))
    coherence = resonance * n_penalty * n_res * np.exp(- (Z_magic_dist + N_magic_dist + ratio_penalty))
    if t3_coupling > 0 and abs(branch_mix) < 0.5:
        coherence = coherence * (1.0 - t3_coupling) + t3_coupling * 0.8
    return np.clip(coherence, 0.0, 1.0)

def half_life_from_coherence(coh, ref_coh=0.45, ref_hl=0.08, beta=8.0):
    safe_coh = max(1e-6, min(0.999999, coh))
    log_hl = np.log(ref_hl) + beta * (safe_coh - ref_coh) / (1.0 - safe_coh + 1e-6)
    return np.exp(log_hl)

# -------------------------------------------------------------------------
# DRUG SCREENING MODULE WITH SCALAR WAVE INTEGRATION (CORRECTED)
# -------------------------------------------------------------------------
def molecular_harmonic_index(mw):
    return np.log(mw) / np.log(ANCHOR_DEFAULT) * 0.7

def coherence_drug_target(drug_desc, target_desc, anchor_hz=ANCHOR_DEFAULT,
                          ratio_19_13=RATIO_DEFAULT, cutoff_hz=CUTOFF_DEFAULT,
                          exponent_n=N_DEFAULT, phase_deg=0.0, scalar_mode=False,
                          scalar_dir=1/9):   # CORRECTED: random orientation factor = 1/9
    """
    Compute harmonic coherence between a drug and a target.
    If scalar_mode=True, the coherence is multiplied by:
        - scalar_dir (1/9 for random orientation, 1 for perfect alignment)
        - phase_factor = (1+cos(phase_rad))/2  (0..1)
    """
    A = np.sqrt(drug_desc['mw'] * target_desc['mw']) / 100.0

    # Resonance term
    if 'freqs' in drug_desc and 'freqs' in target_desc and drug_desc['freqs'] and target_desc['freqs']:
        combined = drug_desc['freqs'] + target_desc['freqs']
        prod = 1.0
        for f in combined:
            prod *= (f / anchor_hz)
        f_scale = prod ** (1.0 / len(combined)) if combined else A
    else:
        f_scale = A
    resonance = np.exp(-5.0 * abs(f_scale - round(f_scale)))

    # Magic number proximity
    A_magic_dist = min(abs(A - m) for m in MAGIC_NUMBERS) / 40.0

    # 19:13 ratio penalty
    drug_ratio = drug_desc.get('ratio', ratio_19_13)
    target_ratio = target_desc.get('ratio', ratio_19_13)
    ratio_penalty = (abs(drug_ratio - ratio_19_13) / ratio_19_13 +
                     abs(target_ratio - ratio_19_13) / ratio_19_13) / 2.0

    # 230th subharmonic penalty
    n_eff = A / 230.0
    n_penalty = np.exp(-10.0 * abs(n_eff - round(n_eff)))

    # Dimensional exponent resonance
    n_val = molecular_harmonic_index(target_desc['mw'])
    n_res = np.exp(-2.0 * abs(np.sin(np.pi * (n_val - exponent_n))))

    # Base coherence (without scalar wave factors)
    coherence = resonance * n_penalty * n_res * np.exp(- (A_magic_dist + ratio_penalty))
    coherence = np.clip(coherence, 0.0, 1.0)

    # Apply scalar wave modifications if enabled
    if scalar_mode:
        phase_rad = np.radians(phase_deg)
        phase_factor = (1.0 + np.cos(phase_rad)) / 2.0
        coherence = coherence * scalar_dir * phase_factor
        coherence = np.clip(coherence, 0.0, 1.0)

    return coherence

def handshake_energy(coherence, amplification_base=10000.0, scalar_boost=1.0):
    """If scalar_boost > 1, amplifies the energy when coherence high."""
    if coherence < 0.5:
        return 0.0
    return amplification_base * (coherence ** 2) * scalar_boost

def load_drugs_from_csv(filepath):
    df = pd.read_csv(filepath)
    drugs = {}
    for _, row in df.iterrows():
        freqs = [float(f) for f in str(row['freqs']).split(';')] if pd.notna(row['freqs']) else []
        drugs[row['name']] = {'mw': row['mw'], 'ratio': row['ratio'], 'freqs': freqs}
    return drugs

def load_targets_from_csv(filepath):
    return load_drugs_from_csv(filepath)   # same format

def demo_database():
    drugs = {
        "Aspirin": {"mw": 180.16, "ratio": 1.45, "freqs": [270, 540, 810]},
        "Ibuprofen": {"mw": 206.28, "ratio": 1.44, "freqs": [268, 536]},
        "Atorvastatin": {"mw": 558.64, "ratio": 1.46, "freqs": [269, 538, 807]},
    }
    targets = {
        "COX-2": {"mw": 70000, "ratio": RATIO_DEFAULT, "freqs": [269, 538, 807]},
        "HMG-CoA reductase": {"mw": 120000, "ratio": RATIO_DEFAULT, "freqs": [271, 542, 813]},
    }
    return drugs, targets

def screen_drugs(drugs, targets, phase_deg=0.0, scalar_mode=False, scalar_boost=1.0, threshold=0.7):
    results = []
    for dname, ddesc in drugs.items():
        for tname, tdesc in targets.items():
            coh = coherence_drug_target(ddesc, tdesc, phase_deg=phase_deg, scalar_mode=scalar_mode)
            energy = handshake_energy(coh, scalar_boost=scalar_boost)
            results.append({
                "Drug": dname,
                "Target": tname,
                "Coherence": round(coh, 4),
                "Therapeutic Energy": round(energy, 1),
                "Prediction": "Active" if coh >= threshold else "Inactive"
            })
    df = pd.DataFrame(results)
    return df.sort_values("Coherence", ascending=False)

# -------------------------------------------------------------------------
# EMBEDDED PAPER TEXT (shortened – you can paste full paper)
# -------------------------------------------------------------------------
PAPER_TEXT = """
Harmonic Grand Unified Theory for Rational Drug Design...
(Full paper text here)
"""

def show_paper_window():
    win = tk.Toplevel()
    win.title("Harmonic GUT – Full Paper")
    win.geometry("700x600")
    text_area = ScrolledText(win, wrap=tk.WORD, font=("Courier", 10))
    text_area.pack(fill=tk.BOTH, expand=True)
    text_area.insert(tk.END, PAPER_TEXT)
    text_area.configure(state=tk.DISABLED)
    tk.Button(win, text="Close", command=win.destroy).pack(pady=5)

# =============================================================================
# MAIN INTERACTIVE WINDOW (Nuclear Stability Maps + Drug Screening)
# =============================================================================
Z_vals = np.arange(100, 185, 2, dtype=np.float64)
N_vals = np.arange(140, 401, 2, dtype=np.float64)
extent = [N_vals[0], N_vals[-1], Z_vals[0], Z_vals[-1]]

coherence_init = np.zeros((len(Z_vals), len(N_vals)))
for i, Z in enumerate(Z_vals):
    for j, N in enumerate(N_vals):
        coherence_init[i,j] = coherence_score(Z, N, ANCHOR_DEFAULT, RATIO_DEFAULT,
                                              CUTOFF_DEFAULT, N_DEFAULT, BRANCH_DEFAULT, T3_DEFAULT)

fig, ax = plt.subplots(figsize=(12, 8))
plt.subplots_adjust(bottom=0.5, left=0.1)   # extra space for new sliders

im = ax.imshow(coherence_init, origin='lower', aspect='auto', cmap='hot_r',
               extent=extent, norm=LogNorm(vmin=0.001, vmax=1))
cbar = plt.colorbar(im, ax=ax, label='Harmonic Coherence')

for m in MAGIC_NUMBERS:
    if m >= Z_vals.min() and m <= Z_vals.max():
        ax.axhline(y=m, color='cyan', linestyle='--', alpha=0.6)
    if m >= N_vals.min() and m <= N_vals.max():
        ax.axvline(x=m, color='cyan', linestyle='--', alpha=0.6)
ax.scatter([184], [126], color='lime', s=100, marker='*', label='Z=126,N=184')
ax.legend(loc='upper left')
ax.set_xlabel('Neutron Number (N)')
ax.set_ylabel('Proton Number (Z)')
ax.grid(alpha=0.3)
ax.set_title('Harmonic Framework – Stability Islands (Matter Branch)', fontsize=14)

# -------------------------------------------------------------------------
# Sliders (existing + Phase Offset)
# -------------------------------------------------------------------------
ax_freq = plt.axes([0.2, 0.38, 0.6, 0.03])
freq_slider = Slider(ax_freq, 'Anchor Freq (Hz)', 20.0, 34.0, valinit=ANCHOR_DEFAULT, valstep=0.1)

ax_ratio = plt.axes([0.2, 0.32, 0.6, 0.03])
ratio_slider = Slider(ax_ratio, '19:13 Ratio', 1.30, 1.60, valinit=RATIO_DEFAULT, valstep=0.001)

ax_cutoff = plt.axes([0.2, 0.26, 0.6, 0.03])
cutoff_slider = Slider(ax_cutoff, '230th Cutoff (Hz)', 0.05, 0.30, valinit=CUTOFF_DEFAULT, valstep=0.001)

ax_n = plt.axes([0.2, 0.20, 0.6, 0.03])
n_slider = Slider(ax_n, 'Exponent n', 0.0, 10.0, valinit=N_DEFAULT, valstep=0.01)

ax_branch = plt.axes([0.2, 0.14, 0.6, 0.03])
branch_slider = Slider(ax_branch, 'Branch (+1=matter, -1=anti, 0=T3)', -1.0, 1.0, valinit=BRANCH_DEFAULT, valstep=0.01)

ax_t3 = plt.axes([0.2, 0.08, 0.6, 0.03])
t3_slider = Slider(ax_t3, 'T3 Dark Coupling', 0.0, 1.0, valinit=T3_DEFAULT, valstep=0.01)

# New slider for phase offset (drug screening)
ax_phase = plt.axes([0.2, 0.02, 0.6, 0.03])
phase_slider = Slider(ax_phase, 'Phase Offset (deg)', 0.0, 360.0, valinit=0.0, valstep=1.0)

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
            new_coh[i,j] = coherence_score(Z, N, anchor, ratio, cutoff, n_exp, branch, t3)
    im.set_data(new_coh)
    mode = "Matter Branch" if branch > 0.5 else ("Anti-Matter Branch" if branch < -0.5 else f"Dark Matter (coupling={t3:.2f})")
    ax.set_title(f'Harmonic Framework – {mode}\nAnchor={anchor:.1f} Hz, Ratio={ratio:.4f}, Cutoff={cutoff:.4f} Hz, n={n_exp:.2f}', fontsize=14)
    fig.canvas.draw_idle()

freq_slider.on_changed(update)
ratio_slider.on_changed(update)
cutoff_slider.on_changed(update)
n_slider.on_changed(update)
branch_slider.on_changed(update)
t3_slider.on_changed(update)

def add_green_marker(slider, value, label):
    asl = slider.ax
    vmin, vmax = slider.valmin, slider.valmax
    norm = (value - vmin) / (vmax - vmin)
    asl.axvline(x=norm, color='green', linewidth=2, alpha=0.7)
    asl.text(norm, -0.6, label, transform=asl.transAxes, ha='center', va='top', color='green')

add_green_marker(freq_slider, ANCHOR_DEFAULT, '27 Hz')
add_green_marker(ratio_slider, RATIO_DEFAULT, '19/13')
add_green_marker(cutoff_slider, CUTOFF_DEFAULT, f'{CUTOFF_DEFAULT:.3f} Hz')
add_green_marker(n_slider, N_DEFAULT, f'n={N_DEFAULT}')
add_green_marker(branch_slider, BRANCH_DEFAULT, 'Matter (+1)')
add_green_marker(t3_slider, T3_DEFAULT, 'T3=0')
add_green_marker(phase_slider, 0.0, '0° (in-phase)')

# -------------------------------------------------------------------------
# Buttons (existing + Scalar Mode toggle + Scatter Plot)
# -------------------------------------------------------------------------
ax_compare = plt.axes([0.05, 0.01, 0.10, 0.04])
compare_btn = Button(ax_compare, 'Compare T1/T2/T3', color='lightgray', hovercolor='yellow')
def show_comparison(event):
    anchor, ratio, cutoff, n_exp, t3 = freq_slider.val, ratio_slider.val, cutoff_slider.val, n_slider.val, t3_slider.val
    matter = np.array([[coherence_score(Z, N, anchor, ratio, cutoff, n_exp, 1.0, t3) for N in N_vals] for Z in Z_vals])
    anti   = np.array([[coherence_score(Z, N, anchor, ratio, cutoff, n_exp, -1.0, t3) for N in N_vals] for Z in Z_vals])
    dark   = np.array([[coherence_score(Z, N, anchor, ratio, cutoff, n_exp, 0.0, t3) for N in N_vals] for Z in Z_vals])
    fig2, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18,6))
    ax1.imshow(matter, origin='lower', extent=extent, norm=LogNorm(0.001,1), cmap='hot_r')
    ax1.set_title('Matter (T1)')
    ax2.imshow(anti, origin='lower', extent=extent, norm=LogNorm(0.001,1), cmap='hot_r')
    ax2.set_title('Anti‑Matter (T2)')
    ax3.imshow(dark, origin='lower', extent=extent, norm=LogNorm(0.001,1), cmap='hot_r')
    ax3.set_title('Dark Matter (T3)')
    for axs in (ax1,ax2,ax3):
        axs.set_xlabel('N'); axs.set_ylabel('Z')
    plt.tight_layout()
    plt.show()
compare_btn.on_clicked(show_comparison)

ax_table = plt.axes([0.16, 0.01, 0.10, 0.04])
table_btn = Button(ax_table, 'Extended Table', color='lightgray', hovercolor='yellow')
def show_extended_table(event):
    print("Extended table – see previous implementation (placeholder).")
table_btn.on_clicked(show_extended_table)

# Scalar Wave Mode toggle
ax_scalar_toggle = plt.axes([0.27, 0.01, 0.10, 0.04])
scalar_btn = Button(ax_scalar_toggle, 'Scalar Mode OFF', color='lightgray', hovercolor='yellow')
scalar_enabled = False
def toggle_scalar(event):
    global scalar_enabled
    scalar_enabled = not scalar_enabled
    scalar_btn.label.set_text('Scalar Mode ON' if scalar_enabled else 'Scalar Mode OFF')
    print(f"Scalar wave mode {'enabled' if scalar_enabled else 'disabled'}")
scalar_btn.on_clicked(toggle_scalar)

# Drug Screening button
ax_drug = plt.axes([0.38, 0.01, 0.10, 0.04])
drug_btn = Button(ax_drug, 'Drug Screen', color='lightgray', hovercolor='yellow')
last_drugs = None
last_targets = None
def run_drug_screen(event):
    global last_drugs, last_targets
    if os.path.exists("drugs.csv") and os.path.exists("targets.csv"):
        drugs = load_drugs_from_csv("drugs.csv")
        targets = load_targets_from_csv("targets.csv")
    else:
        drugs, targets = demo_database()
        print("Using demo database. Place drugs.csv and targets.csv for real screening.")
    last_drugs, last_targets = drugs, targets
    phase = phase_slider.val
    scalar_boost = 5.0 if scalar_enabled else 1.0
    results = screen_drugs(drugs, targets, phase_deg=phase, scalar_mode=scalar_enabled, scalar_boost=scalar_boost)
    print("\n" + "="*60)
    print("Harmonic Drug Screening Results")
    print(results.to_string(index=False))
    # Show table
    fig2, ax2 = plt.subplots(figsize=(8,4))
    ax2.axis('off')
    ax2.table(cellText=results.values, colLabels=results.columns, loc='center')
    ax2.set_title("Drug‑Target Coherence Predictions")
    plt.show()
    results.to_csv("drug_screen_results.csv", index=False)
    print("Results saved to drug_screen_results.csv")
drug_btn.on_clicked(run_drug_screen)

# Scatter Plot button
ax_scatter = plt.axes([0.49, 0.01, 0.10, 0.04])
scatter_btn = Button(ax_scatter, 'Scatter Plot', color='lightgray', hovercolor='yellow')
def make_scatter(event):
    try:
        drugs = last_drugs
        targets = last_targets
    except NameError:
        print("No drug screening performed yet. Click 'Drug Screen' first.")
        return
    # Use first drug and first target for simplicity
    dname = list(drugs.keys())[0]
    tname = list(targets.keys())[0]
    print(f"Plotting coherence vs phase offset for {dname} → {tname}")
    phases = np.linspace(0, 360, 361)
    coherences = []
    for ph in phases:
        coh = coherence_drug_target(drugs[dname], targets[tname], phase_deg=ph, scalar_mode=scalar_enabled)
        coherences.append(coh)
    fig2, ax2 = plt.subplots()
    ax2.plot(phases, coherences, 'b-')
    ax2.set_xlabel('Phase Offset (degrees)')
    ax2.set_ylabel('Coherence')
    ax2.set_title(f'{dname} → {tname}\nScalar mode {"ON" if scalar_enabled else "OFF"}')
    ax2.grid(True)
    ax2.set_ylim(0, 1)
    plt.show()
scatter_btn.on_clicked(make_scatter)

# Paper button
ax_paper = plt.axes([0.60, 0.01, 0.10, 0.04])
paper_btn = Button(ax_paper, 'Show Paper', color='lightgray', hovercolor='yellow')
paper_btn.on_clicked(lambda event: show_paper_window())

# Handshake buttons (placeholders)
ax_hs12 = plt.axes([0.71, 0.01, 0.10, 0.04])
hs12_btn = Button(ax_hs12, 'Handshake T1-T2', color='lightgray', hovercolor='yellow')
def run_hs12(event):
    cutoff = cutoff_slider.val
    fig2, ax2 = plt.subplots()
    ax2.set_title(f'T1-T2 Handshake at {cutoff:.4f} Hz')
    ax2.plot([0,1],[0,1])
    plt.show()
hs12_btn.on_clicked(run_hs12)

ax_hs13 = plt.axes([0.82, 0.01, 0.10, 0.04])
hs13_btn = Button(ax_hs13, 'Handshake T1-T3', color='lightgray', hovercolor='yellow')
hs13_btn.on_clicked(lambda event: plt.figure() or plt.title('T1-T3 handshake') or plt.show())

plt.show()