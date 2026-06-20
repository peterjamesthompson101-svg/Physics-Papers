#!/usr/bin/env python3
# sam_bh_client.py

import socket
import struct
import json
import sys

class SamBHClient:
    def __init__(self, host='localhost', port=8889):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))

    def disconnect(self):
        if self.sock:
            self.sock.close()

    def send_command(self, cmd: str, data: dict = None):
        message = json.dumps({"cmd": cmd, "data": data or {}})
        msg_len = struct.pack('!I', len(message))
        self.sock.sendall(msg_len + message.encode('utf-8'))

    def receive_response(self):
        len_data = self.sock.recv(4)
        if not len_data:
            raise ConnectionError("No response")
        resp_len = struct.unpack('!I', len_data)[0]
        resp_data = b''
        while len(resp_data) < resp_len:
            chunk = self.sock.recv(min(4096, resp_len - len(resp_data)))
            if not chunk:
                raise ConnectionError("Connection closed")
            resp_data += chunk
        return json.loads(resp_data.decode('utf-8'))

    def load_spectrum(self, mass, spectrum):
        """Send a spectrum to Sam for analysis."""
        self.send_command("load", {"mass": mass, "spectrum": spectrum})
        return self.receive_response()

    def detect(self, mass):
        """Request harmonic comb detection."""
        self.send_command("detect", {"mass": mass})
        return self.receive_response()

    def teach(self, concept):
        """Teach Sam a concept."""
        self.send_command("teach", {"concept": concept})
        return self.receive_response()

    def teach_bh(self):
        """Teach Sam the black hole harmonic comb concept."""
        return self.teach("black_hole_harmonic_comb")

    def status(self):
        """Get Sam's learning status."""
        self.send_command("status")
        return self.receive_response()

    def knowledge(self, concept):
        """Get Sam's knowledge about a concept."""
        self.send_command("knowledge", {"concept": concept})
        return self.receive_response()

    def list(self):
        """List mastered concepts."""
        self.send_command("list")
        return self.receive_response()

# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    client = SamBHClient()
    try:
        client.connect()
        print("Connected to Sam's Black Hole Phase Reader")
        print("Teaching Sam the black hole harmonic comb concept...")
        result = client.teach_bh()
        print(f"Teach result: {result}")

        print("Loading a test spectrum for M = 10 M☉...")
        # Generate a simple test spectrum
        import math
        import random
        spectrum = []
        for i in range(32):
            k = i + 1
            amp = 1.0 / (k + 0.1)
            phase = k * (-1.0 * math.pi / 180.0)
            spectrum.append(amp * math.cos(phase) + random.gauss(0, 0.05))
        result = client.load_spectrum(10.0, spectrum)
        print(f"Load result: {result}")

        print("Detecting harmonic comb...")
        result = client.detect(10.0)
        print(f"Detection result: {result}")

        print("Sam's status:")
        print(client.status())

    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.disconnect()