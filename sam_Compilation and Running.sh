# Install dependencies
sudo apt install nlohmann-json3-dev libssl-dev

# Compile
g++ -std=c++17 -O3 -march=native -pthread -o bh_reader_sam black_hole_reader_with_sam.cpp -lssl -lcrypto

# Run the interactive system
./bh_reader_sam

# In another terminal, run the Python client
python3 sam_bh_client.py