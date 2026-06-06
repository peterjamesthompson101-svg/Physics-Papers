#!/usr/bin/env python3
"""
Extract molecular data from MVE repository (.dat + .mol) to a CSV file.
Usage: python extract_mve_to_csv.py
"""

import os
import re
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Descriptors

# =============================================================================
# Helper functions
# =============================================================================
def parse_dat_frequencies(dat_path):
    """
    Read a .dat file and return a list of vibrational frequencies (in cm^-1).
    Format: each line starts with a frequency (float) followed by other numbers.
    """
    freqs = []
    with open(dat_path, 'r') as f:
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

def process_mol_file(mol_path):
    """
    Use RDKit to load a .mol file and return (SMILES, molecular weight).
    """
    mol = Chem.MolFromMolFile(mol_path)
    if mol is None:
        return None, None
    smiles = Chem.MolToSmiles(mol)
    mw = Descriptors.MolWt(mol)
    return smiles, mw

def walk_database(root_dir, db_name):
    """
    Walk through a database folder (e.g., data_SAu) and collect records.
    """
    records = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if not fname.endswith('.dat'):
                continue
            dat_path = os.path.join(dirpath, fname)
            base = fname[:-4]   # remove .dat
            mol_path = os.path.join(dirpath, base + '.mol')
            if not os.path.exists(mol_path):
                print(f"Warning: missing .mol for {base}, skipping")
                continue
            
            # Extract frequencies
            freqs = parse_dat_frequencies(dat_path)
            if not freqs:
                print(f"Warning: no frequencies found in {dat_path}")
                continue
            
            # Get SMILES and MW from .mol
            smiles, mw = process_mol_file(mol_path)
            if smiles is None:
                print(f"Warning: could not parse .mol file {mol_path}, skipping")
                continue
            
            # Use the base name as identifier (e.g., "10085066")
            name = base
            # For ratio, we set the ideal 19/13. You can later replace with a computed property.
            ratio = 19.0 / 13.0   # ≈1.4615
            
            records.append({
                'name': name,
                'smiles': smiles,
                'mw': mw,
                'ratio': ratio,
                'freqs': freqs,
                'database': db_name
            })
            print(f"Processed {name} (MW={mw:.2f}, {len(freqs)} freqs)")
    return records

# =============================================================================
# Main
# =============================================================================
def main():
    # Adjust these paths if you run from a different location
    repo_root = '.'   # assumes script is run from MVE root
    output_csv = 'molecules.csv'
    
    all_records = []
    for subdb in ['data_SAu', 'data_SH']:
        db_path = os.path.join(repo_root, subdb)
        if not os.path.isdir(db_path):
            print(f"Warning: {db_path} not found")
            continue
        print(f"\nProcessing {subdb}...")
        records = walk_database(db_path, subdb)
        all_records.extend(records)
        print(f"Found {len(records)} valid molecules.")
    
    if not all_records:
        print("No data extracted. Check paths and that .mol files exist.")
        return
    
    # Convert to DataFrame and save as CSV
    df = pd.DataFrame(all_records)
    # Convert frequency list to semicolon-separated string
    df['freqs_str'] = df['freqs'].apply(lambda x: ';'.join(f'{f:.1f}' for f in x))
    df = df.drop(columns=['freqs'])
    df.rename(columns={'freqs_str': 'freqs'}, inplace=True)
    
    # Keep only columns needed for drug screening (name, mw, ratio, freqs)
    # Also keep smiles for reference but not used in coherence calculation.
    df_out = df[['name', 'smiles', 'mw', 'ratio', 'freqs']]
    df_out.to_csv(output_csv, index=False)
    print(f"\nSaved {len(df_out)} molecules to {output_csv}")

if __name__ == '__main__':
    main()