# Create a clean environment (recommended)
conda create -n gut_screening python=3.9
conda activate gut_screening

# Install ProDy and Biopython
conda install -c conda-forge prody biopython

# Install other dependencies
conda install numpy pandas matplotlib