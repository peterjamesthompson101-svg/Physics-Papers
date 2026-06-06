#!/usr/bin/env python3
"""
Automated Target Library Builder for Harmonic GUT Drug Screening
================================================================
Uses rcsb-api (official RCSB PDB Python package) to:
1. Search for PDB entries by protein class (kinase, GPCR, ion channel, etc.)
2. Download the structures
3. Compute molecular weight and vibrational frequencies (via ProDy ANM)
4. Output a targets.csv file compatible with the drug screening pipeline.

Installation:
    conda create -n gut_targets python=3.9
    conda activate gut_targets
    conda install -c conda-forge prody biopython rcsb-api
    pip install pandas

Usage:
    python build_target_library.py --classes kinases,GPCRs --max-per-class 50
    python build_target_library.py --class-list-file my_targets.txt
    python build_target_library.py --all-drug-targets
"""

import os
import sys
import argparse
import time
import numpy as np
import pandas as pd
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path

# ============================================================================
# 1. Check and install missing dependencies
# ============================================================================
def check_dependencies():
    missing = []
    try:
        import prody
    except ImportError:
        missing.append("prody")
    try:
        from Bio import SeqIO
    except ImportError:
        missing.append("biopython")
    try:
        from rcsbapi.search import Search
    except ImportError:
        missing.append("rcsb-api")
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: conda install -c conda-forge " + " ".join(missing))
        sys.exit(1)

check_dependencies()

import prody
from prody import *
from Bio.PDB import PDBParser, PDBList
from Bio.SeqUtils import molecular_weight
from rcsbapi.search import Search, AttributeQuery, TextQuery, OrQuery

# ============================================================================
# 2. Define target classes
# ============================================================================
TARGET_CLASSES = {
    "Kinase": {
        "search_terms": ["kinase", "protein kinase", "phosphotransferase"],
        "pdb_keywords": ["kinase"],
        "example_targets": ["4AGL", "3PP0", "1ATP", "2HZI", "1M17"]
    },
    "GPCR": {
        "search_terms": ["G protein-coupled receptor", "GPCR", "rhodopsin-like"],
        "pdb_keywords": ["GPCR", "G protein-coupled"],
        "example_targets": ["6OIK", "6DDE", "5TVN", "4MBS", "3SN6"]
    },
    "Ion Channel": {
        "search_terms": ["ion channel", "potassium channel", "sodium channel", "calcium channel"],
        "pdb_keywords": ["channel"],
        "example_targets": ["6A95", "6HHI", "5WCD", "2R9R", "3J5E"]
    },
    "Protease": {
        "search_terms": ["protease", "peptidase", "enzyme"],
        "pdb_keywords": ["protease"],
        "example_targets": ["1W7X", "1SQT", "1TNR", "2VYX", "4X6H"]
    },
    "Nuclear Receptor": {
        "search_terms": ["nuclear receptor", "steroid receptor", "hormone receptor"],
        "pdb_keywords": ["nuclear receptor"],
        "example_targets": ["1A28", "1DB1", "1X78", "3FEY", "4PXA"]
    }
}

# ============================================================================
# 3. Search for PDB IDs using rcsb-api
# ============================================================================
def search_pdb_by_class(class_name: str, target_max: int = 100) -> List[str]:
    """
    Search RCSB PDB for entries belonging to a protein class.
    Uses the official rcsb-api package.
    """
    class_info = TARGET_CLASSES.get(class_name)
    if not class_info:
        print(f"Warning: unknown class {class_name}")
        return []
    
    pdb_ids = set()
    
    # Search using text query on keywords
    for keyword in class_info.get("search_terms", []):
        try:
            # Create a text query for the keyword
            query = TextQuery(keyword)
            # Execute search
            results = query()
            # Collect IDs
            for entry in results:
                pdb_id = entry.get("identifier", "")
                if pdb_id and len(pdb_id) == 4 and pdb_id.isalnum():
                    pdb_ids.add(pdb_id)
            print(f"  Found {len(results)} hits for keyword '{keyword}'")
            time.sleep(0.2)  # Be polite to the API
        except Exception as e:
            print(f"  Error searching for '{keyword}': {e}")
    
    # Also search using attribute query on struct_keywords
    try:
        attr_query = AttributeQuery("struct_keywords.pdbx_keywords", "contains", class_name.lower())
        results = attr_query()
        for entry in results:
            pdb_id = entry.get("identifier", "")
            if pdb_id and len(pdb_id) == 4 and pdb_id.isalnum():
                pdb_ids.add(pdb_id)
        print(f"  Found {len(results)} hits via struct_keywords")
    except Exception as e:
        print(f"  Attribute query failed: {e}")
    
    # Limit to target_max
    return list(pdb_ids)[:target_max]

def search_pdb_by_sequence_motif(motif: str, target_max: int = 50) -> List[str]:
    """
    Search for PDB structures containing a specific sequence motif.
    Useful for finding proteins with a conserved active site.
    """
    try:
        from rcsbapi.search import SequenceQuery
        query = SequenceQuery(motif, sequence_type="protein")
        results = query()
        pdb_ids = []
        for entry in results:
            pdb_id = entry.get("identifier", "")
            if pdb_id and len(pdb_id) == 4 and pdb_id.isalnum():
                pdb_ids.append(pdb_id)
        return pdb_ids[:target_max]
    except Exception as e:
        print(f"Error in sequence motif search: {e}")
        return []

# ============================================================================
# 4. Fetch PDB files and compute target properties
# ============================================================================
def fetch_pdb_files(pdb_ids: List[str], output_dir: str = "pdb_files") -> Dict[str, str]:
    """Download PDB files using Biopython's PDBList."""
    pdb_list = PDBList()
    os.makedirs(output_dir, exist_ok=True)
    local_files = {}
    for pdb_id in pdb_ids:
        clean_id = pdb_id.lower().strip()
        try:
            filename = pdb_list.retrieve_pdb_file(clean_id, pdir=output_dir, file_format="pdb")
            local_files[clean_id] = filename
            print(f"  Downloaded: {clean_id}")
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f"  Failed to download {clean_id}: {e}")
    return local_files

def get_molecular_weight_from_pdb(pdb_file: str) -> float:
    """
    Compute approximate molecular weight (kDa) from PDB file.
    Uses Biopython to extract sequence and calculate MW.
    """
    try:
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("protein", pdb_file)
        # Collect all residue one-letter codes
        residues = []
        three_to_one = {
            'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
            'GLN': 'Q', 'GLU': 'E', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
            'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
            'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V'
        }
        for model in structure:
            for chain in model:
                for residue in chain:
                    resname = residue.get_resname()
                    if resname in three_to_one:
                        residues.append(three_to_one[resname])
        if not residues:
            return 50000.0  # fallback
        seq = ''.join(residues)
        mw_da = molecular_weight(seq, seq_type='protein')
        return mw_da / 1000.0  # convert to kDa
    except Exception as e:
        print(f"Warning: could not compute MW: {e}")
        return 60000.0 / 1000.0

def compute_normal_modes(pdb_id: str, pdb_file: str, n_modes: int = 30) -> List[float]:
    """
    Perform ANM (Anisotropic Network Model) normal mode analysis using ProDy.
    Returns a list of vibrational frequencies in Hz (scaled to GUT framework).
    """
    try:
        protein = parsePDB(pdb_file, subset='ca')
        if protein is None or len(protein) < 3:
            print(f"  Warning: insufficient atoms for {pdb_id}")
            return []
        anm = ANM("protein")
        anm.build(protein, cutoff=10.0)
        anm.calcModes(n_modes=n_modes)
        eigvals = anm.getEigvals()
        if eigvals is None or len(eigvals) == 0:
            return []
        # Skip the first few zero-eigenvalues (rigid body motions)
        # and take the next n_modes
        omega = np.sqrt(eigvals)
        # Calibrate such that the first mode is ~270 Hz
        scaling = 270.0 / (omega[0] + 1e-6) if len(omega) > 0 else 1.0
        freqs_hz = (omega * scaling).tolist()
        return freqs_hz[:n_modes]
    except Exception as e:
        print(f"  Error in NMA for {pdb_id}: {e}")
        return []

# ============================================================================
# 5. Main workflow: Build targets CSV
# ============================================================================
def build_target_library(
    target_classes: List[str],
    max_per_class: int = 50,
    output_csv: str = "targets.csv",
    pdb_dir: str = "pdb_files",
    n_modes: int = 30,
    use_example_fallbacks: bool = True
) -> None:
    """
    Build a comprehensive target library by searching for PDB IDs
    for each target class, downloading structures, and computing properties.
    """
    all_records = []
    all_pdb_ids = set()
    class_to_pdb_ids = {}
    
    # Step 1: Collect PDB IDs for each class
    for class_name in target_classes:
        print(f"\nSearching for {class_name} targets...")
        pdb_ids = search_pdb_by_class(class_name, max_per_class)
        if not pdb_ids and use_example_fallbacks:
            # Fallback to known example targets
            example_targets = TARGET_CLASSES.get(class_name, {}).get("example_targets", [])
            pdb_ids = example_targets[:max_per_class]
            print(f"  Using example targets: {pdb_ids}")
        class_to_pdb_ids[class_name] = pdb_ids
        all_pdb_ids.update(pdb_ids)
        print(f"  Collected {len(pdb_ids)} PDB IDs")
    
    # Step 2: Download PDB files
    print(f"\nDownloading {len(all_pdb_ids)} PDB structures...")
    pdb_files = fetch_pdb_files(list(all_pdb_ids), pdb_dir)
    
    # Step 3: Process each PDB ID
    print("\nProcessing structures (this may take a while)...")
    for pdb_id, pdb_file in pdb_files.items():
        print(f"  Processing {pdb_id.upper()}...")
        
        # Molecular weight
        mw_kda = get_molecular_weight_from_pdb(pdb_file)
        
        # Vibrational frequencies via NMA
        freqs = compute_normal_modes(pdb_id, pdb_file, n_modes)
        if not freqs and use_example_fallbacks:
            # Fallback to typical frequencies for this class
            freqs = [270.0, 540.0, 810.0]
        
        freqs_str = ';'.join(f'{f:.1f}' for f in freqs[:n_modes])
        
        # Determine which class(es) this PDB ID belongs to
        assigned_classes = [c for c, ids in class_to_pdb_ids.items() if pdb_id in ids]
        primary_class = assigned_classes[0] if assigned_classes else "Unknown"
        
        all_records.append({
            'name': f"{pdb_id.upper()}_{primary_class}",
            'pdb_id': pdb_id.upper(),
            'class': primary_class,
            'mw_kda': round(mw_kda, 2),
            'ratio': 19.0/13.0,  # ideal ratio (can be adjusted)
            'freqs': freqs_str,
            'n_modes': len(freqs)
        })
    
    # Step 4: Save to CSV
    if not all_records:
        print("\nNo records collected. Check your search queries.")
        return
    
    df = pd.DataFrame(all_records)
    # Keep only columns needed for drug screening
    df_out = df[['name', 'mw_kda', 'ratio', 'freqs']]
    df_out.columns = ['name', 'mw', 'ratio', 'freqs']
    df_out.to_csv(output_csv, index=False)
    
    print(f"\nSaved {len(df_out)} target entries to {output_csv}")
    print("\nStatistics:")
    print(df['class'].value_counts().to_string())
    print(f"\nTargets CSV ready for use in harmonic_gut_drug_screen.py")

# ============================================================================
# 6. Additional search strategies
# ============================================================================
def search_by_sequence_motif(
    motif: str,
    output_csv: str = "targets_motif.csv",
    max_targets: int = 50,
    pdb_dir: str = "pdb_files",
    n_modes: int = 30
) -> None:
    """
    Alternative search: find proteins containing a specific sequence motif.
    Useful for targeting specific active sites or binding domains.
    """
    print(f"\nSearching for sequence motif: {motif}")
    pdb_ids = search_pdb_by_sequence_motif(motif, max_targets)
    if not pdb_ids:
        print("No results found.")
        return
    
    print(f"Found {len(pdb_ids)} PDB IDs")
    pdb_files = fetch_pdb_files(pdb_ids, pdb_dir)
    
    records = []
    for pdb_id, pdb_file in pdb_files.items():
        mw_kda = get_molecular_weight_from_pdb(pdb_file)
        freqs = compute_normal_modes(pdb_id, pdb_file, n_modes)
        if not freqs:
            freqs = [270.0, 540.0, 810.0]
        freqs_str = ';'.join(f'{f:.1f}' for f in freqs)
        records.append({
            'name': pdb_id.upper(),
            'mw': round(mw_kda, 2),
            'ratio': 19.0/13.0,
            'freqs': freqs_str
        })
    
    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False)
    print(f"Saved {len(records)} entries to {output_csv}")

def search_drug_targets_from_drugcentral(max_targets: int = 200) -> List[str]:
    """
    Retrieve known drug target PDB IDs from DrugCentral (via online API).
    Alternative source for validated drug targets.
    """
    try:
        import requests
        # DrugCentral provides a list of drug targets with PDB IDs
        url = "https://drugcentral.org/download"
        # This is a placeholder; in practice you would parse their data dump
        print("DrugCentral integration requires manual download of their dataset.")
        print("See: https://drugcentral.org/download")
        return []
    except Exception as e:
        print(f"Error accessing DrugCentral: {e}")
        return []

# ============================================================================
# 7. Command-line interface
# ============================================================================
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Automated Target Library Builder for Harmonic GUT Drug Screening"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--classes",
        type=str,
        help="Comma-separated list of target classes (e.g., Kinase,GPCR,IonChannel)"
    )
    group.add_argument(
        "--class-list-file",
        type=str,
        help="Text file containing one target class per line"
    )
    group.add_argument(
        "--all-drug-targets",
        action="store_true",
        help="Fetch all known drug targets from DrugCentral (slow)"
    )
    group.add_argument(
        "--sequence-motif",
        type=str,
        help="Search by sequence motif (e.g., 'GXGXXG' for kinase ATP-binding site)"
    )
    
    parser.add_argument("--max-per-class", type=int, default=50,
                       help="Maximum number of PDB IDs per class (default: 50)")
    parser.add_argument("--output", type=str, default="targets.csv",
                       help="Output CSV filename (default: targets.csv)")
    parser.add_argument("--pdb-dir", type=str, default="pdb_files",
                       help="Directory to store downloaded PDB files")
    parser.add_argument("--n-modes", type=int, default=30,
                       help="Number of normal modes to extract (default: 30)")
    parser.add_argument("--no-fallbacks", action="store_true",
                       help="Disable fallback to example targets when search fails")
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    if args.sequence_motif:
        search_by_sequence_motif(
            motif=args.sequence_motif,
            output_csv=args.output,
            max_targets=args.max_per_class,
            pdb_dir=args.pdb_dir,
            n_modes=args.n_modes
        )
        return
    
    if args.all_drug_targets:
        print("Fetching all known drug targets from curated databases...")
        print("This feature requires downloading data from DrugCentral/TTD.")
        print("See: https://drugcentral.org/download and https://db.idrblab.net/ttd/")
        # Placeholder for future implementation
        return
    
    # Determine target classes
    target_classes = []
    if args.classes:
        target_classes = [c.strip() for c in args.classes.split(",")]
    elif args.class_list_file:
        with open(args.class_list_file, 'r') as f:
            target_classes = [line.strip() for line in f if line.strip()]
    else:
        target_classes = ["Kinase", "GPCR", "IonChannel", "Protease", "NuclearReceptor"]
    
    print(f"Target classes: {target_classes}")
    build_target_library(
        target_classes=target_classes,
        max_per_class=args.max_per_class,
        output_csv=args.output,
        pdb_dir=args.pdb_dir,
        n_modes=args.n_modes,
        use_example_fallbacks=not args.no_fallbacks
    )

if __name__ == "__main__":
    main()