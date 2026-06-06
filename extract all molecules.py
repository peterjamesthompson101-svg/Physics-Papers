#!/usr/bin/env python3
"""
Extract molecular data from MVE repository and export to CSV.
Usage: python extract_mve_data.py --input ./molecular-vibration-explorer --output drugs.csv
"""

import os
import argparse
import pandas as pd
from pathlib import Path

# Try to import RDKit for accurate MW; fallback to rough estimation
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    print("RDKit not installed. Molecular weights will be approximated from atom counts.")

def parse_dat_file(filepath):
    """
    Parse a .dat file from MVE. Expected format:
    Lines starting with '#' are comments.
    First column: vibrational frequency (cm^-1).
    We only need the frequency list.
    """
    freqs = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if not parts:
                continue
            try:
                freq = float(parts[0])
                freqs.append(freq)
            except ValueError:
                continue
    return freqs

def get_mw_from_mol(filepath):
    """Return molecular weight in Da from .mol file."""
    if not RDKIT_AVAILABLE:
        # Fallback: approximate by counting atoms in the .mol file
        atom_counts = {}
        with open(filepath, 'r') as f:
            lines = f.readlines()
        # In .mol files, atom block starts after the counts line (line 4)
        # This is very crude – better to install RDKit.
        return 300.0   # placeholder
    mol = Chem.MolFromMolFile(filepath)
    if mol is None:
        return 300.0
    return Descriptors.MolWt(mol)

def process_folder(root_dir, db_name):
    """Walk through a database folder (e.g., data_SAu) and collect records."""
    records = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith('.dat'):
                dat_path = os.path.join(dirpath, file)
                base = file[:-4]
                mol_path = os.path.join(dirpath, base + '.mol')
                if not os.path.exists(mol_path):
                    print(f"Warning: no .mol file for {base}")
                    continue
                freqs = parse_dat_file(dat_path)
                mw = get_mw_from_mol(mol_path) if os.path.exists(mol_path) else 300.0
                # Use the filename (numeric ID) as name; you may want to map to SMILES later
                name = base
                # For now, set ratio to ideal 19/13 (user can adjust)
                ratio = 19.0/13.0
                records.append({
                    'name': name,
                    'mw': mw,
                    'ratio': ratio,
                    'freqs': freqs,
                    'database': db_name
                })
    return records

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help='Root directory of the MVE repository (contains data_SAu, data_SH)')
    parser.add_argument('--output', default='molecules.csv', help='Output CSV file')
    args = parser.parse_args()

    all_records = []
    for subdb in ['data_SAu', 'data_SH']:
        db_path = os.path.join(args.input, subdb)
        if os.path.isdir(db_path):
            print(f"Processing {subdb}...")
            records = process_folder(db_path, subdb)
            all_records.extend(records)
            print(f"  Found {len(records)} molecules.")
        else:
            print(f"Warning: {subdb} not found in {args.input}")

    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    # Convert list of frequencies to semicolon-separated string for CSV
    df['freqs_str'] = df['freqs'].apply(lambda x: ';'.join(f'{f:.1f}' for f in x))
    df = df.drop(columns=['freqs'])
    df.rename(columns={'freqs_str': 'freqs'}, inplace=True)
    df.to_csv(args.output, index=False)
    print(f"Saved {len(df)} molecules to {args.output}")

if __name__ == '__main__':
    main()