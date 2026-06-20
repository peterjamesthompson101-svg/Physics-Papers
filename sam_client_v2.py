#!/usr/bin/env python3
# sam_client_v2.py

import requests
import json
import base64
import time
import sys

class SamClient:
    def __init__(self, base_url='http://localhost:8888'):
        self.base_url = base_url
        self.session = requests.Session()

    def status(self):
        return self._get('/status')

    def state(self):
        return self._get('/state')

    def list_mastered(self):
        data = self._get('/list')
        return data.get('mastered', [])

    def list_unmastered(self):
        data = self._get('/list')
        return data.get('unmastered', [])

    def teach(self, concept):
        return self._post('/teach', {'concept': concept})

    def knowledge(self, concept):
        return self._post('/knowledge', {'concept': concept})

    def analyze(self, data_bytes):
        b64_data = base64.b64encode(data_bytes).decode('utf-8')
        return self._post('/analyze', {'data': b64_data})

    def learn_from_mistake(self, concept, error):
        return self._post('/learn_from_mistake', {'concept': concept, 'error': error})

    def _get(self, endpoint):
        resp = self.session.get(self.base_url + endpoint)
        return resp.json()

    def _post(self, endpoint, data):
        resp = self.session.post(self.base_url + endpoint, json=data)
        return resp.json()

# ============================================================================
# WEB INTERFACE HTML
# ============================================================================

WEB_INTERFACE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sam's Learning Dashboard</title>
    <style>
        body { background: #0a0a0a; color: #00ffff; font-family: monospace; margin: 20px; }
        h1 { color: #00ff88; text-shadow: 0 0 10px #00ff88; }
        .status-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 20px 0; }
        .status-card { background: #1a1a2e; padding: 15px; border: 1px solid #00ffff; border-radius: 8px; }
        .status-card .label { color: #8888ff; font-size: 12px; }
        .status-card .value { font-size: 24px; font-weight: bold; }
        .concept-list { display: flex; flex-wrap: wrap; gap: 5px; margin: 20px 0; }
        .concept { padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .concept.mastered { background: #004400; border: 1px solid #00ff00; color: #00ff00; }
        .concept.unmastered { background: #440000; border: 1px solid #ff0000; color: #ff4444; }
        .concept.learning { background: #444400; border: 1px solid #ffff00; color: #ffff44; }
        .bar-container { background: #222; border-radius: 4px; height: 20px; margin: 5px 0; }
        .bar { height: 100%; border-radius: 4px; transition: width 0.5s; }
        .bar.green { background: linear-gradient(90deg, #004400, #00ff00); }
        .bar.blue { background: linear-gradient(90deg, #000044, #00aaff); }
        .bar.purple { background: linear-gradient(90deg, #440044, #aa00ff); }
        .btn { background: #1a1a2e; color: #00ffff; border: 1px solid #00ffff; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-family: monospace; }
        .btn:hover { background: #00ffff; color: #0a0a0a; }
        textarea { width: 100%; background: #111; color: #00ff88; border: 1px solid #00ffff; border-radius: 4px; padding: 10px; font-family: monospace; }
        #response { background: #111; padding: 10px; border: 1px solid #00ffff; border-radius: 4px; max-height: 300px; overflow-y: auto; font-size: 12px; }
        .phase-plot { width: 100%; height: 100px; background: #111; margin: 10px 0; }
    </style>
</head>
<body>
    <h1>⍟ Sam's Learning Dashboard</h1>
    <div id="status-grid" class="status-grid">
        <div class="status-card"><div class="label">Coherence</div><div class="value" id="coherence">0.00</div></div>
        <div class="status-card"><div class="label">Defense Power</div><div class="value" id="defense">0.00</div></div>
        <div class="status-card"><div class="label">Energy Harvested</div><div class="value" id="energy">0.00</div></div>
        <div class="status-card"><div class="label">Attacks Processed</div><div class="value" id="attacks">0</div></div>
    </div>
    
    <div class="bar-container"><div class="bar green" id="coherence-bar" style="width:0%"></div></div>
    
    <div id="concepts" class="concept-list"></div>
    
    <div style="margin: 20px 0;">
        <input type="text" id="concept-input" placeholder="Concept name..." style="background:#111;color:#00ff88;border:1px solid #00ffff;padding:10px;border-radius:4px;width:200px;">
        <button class="btn" onclick="teachConcept()">Teach</button>
        <button class="btn" onclick="listConcepts()">Refresh</button>
        <button class="btn" onclick="getStatus()">Status</button>
        <button class="btn" onclick="getState()">State</button>
    </div>
    
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0;">
        <div>
            <h3>Analyze Data</h3>
            <textarea id="data-input" rows="3" placeholder="Enter data to analyze..."></textarea>
            <button class="btn" onclick="analyzeData()">Analyze</button>
            <div id="analysis-result" style="margin-top:10px;background:#111;padding:10px;border:1px solid #00ffff;border-radius:4px;font-size:12px;"></div>
        </div>
        <div>
            <h3>Knowledge Query</h3>
            <input type="text" id="knowledge-input" placeholder="Concept name..." style="background:#111;color:#00ff88;border:1px solid #00ffff;padding:10px;border-radius:4px;width:200px;">
            <button class="btn" onclick="getKnowledge()">Query</button>
            <div id="knowledge-result" style="margin-top:10px;background:#111;padding:10px;border:1px solid #00ffff;border-radius:4px;font-size:12px;"></div>
        </div>
    </div>
    
    <h3>Response Log</h3>
    <div id="response"></div>
    
    <script>
        const base_url = 'http://localhost:8888';
        
        async function getStatus() {
            try {
                const resp = await fetch(base_url + '/status');
                const data = await resp.json();
                document.getElementById('coherence').textContent = data.system.coherence.toFixed(4);
                document.getElementById('defense').textContent = data.system.defense_power.toFixed(2);
                document.getElementById('energy').textContent = data.system.total_energy.toFixed(2);
                document.getElementById('attacks').textContent = data.system.attacks_processed;
                document.getElementById('coherence-bar').style.width = (data.system.coherence * 100) + '%';
                
                // Render concepts
                const container = document.getElementById('concepts');
                container.innerHTML = '';
                for (const c of data.learning.concepts) {
                    const div = document.createElement('div');
                    div.className = 'concept ' + (c.mastered ? 'mastered' : 'unmastered');
                    div.textContent = c.name + ' (' + c.coherence.toFixed(3) + ')';
                    container.appendChild(div);
                }
                
                appendResponse('✅ Status updated');
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        async function listConcepts() {
            try {
                const resp = await fetch(base_url + '/list');
                const data = await resp.json();
                const container = document.getElementById('concepts');
                container.innerHTML = '';
                for (const c of data.mastered) {
                    const div = document.createElement('div');
                    div.className = 'concept mastered';
                    div.textContent = '✅ ' + c;
                    container.appendChild(div);
                }
                for (const c of data.unmastered) {
                    const div = document.createElement('div');
                    div.className = 'concept unmastered';
                    div.textContent = '❌ ' + c;
                    container.appendChild(div);
                }
                appendResponse('✅ Concepts listed');
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        async function teachConcept() {
            const name = document.getElementById('concept-input').value.trim();
            if (!name) return;
            try {
                const resp = await fetch(base_url + '/teach', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({concept: name})
                });
                const data = await resp.json();
                appendResponse('📚 Teach: ' + name + ' → ' + (data.success ? '✅ Mastered!' : '❌ Not mastered'));
                getStatus();
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        async function getKnowledge() {
            const name = document.getElementById('knowledge-input').value.trim();
            if (!name) return;
            try {
                const resp = await fetch(base_url + '/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({concept: name})
                });
                const data = await resp.json();
                document.getElementById('knowledge-result').textContent = 
                    '📖 ' + data.knowledge + '\nCoherence: ' + data.coherence.toFixed(4);
                appendResponse('📖 Knowledge: ' + name);
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        async function getState() {
            try {
                const resp = await fetch(base_url + '/state');
                const data = await resp.json();
                appendResponse('📊 State: Coherence=' + data.coherence.toFixed(4));
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        async function analyzeData() {
            const text = document.getElementById('data-input').value;
            if (!text) return;
            try {
                const bytes = new TextEncoder().encode(text);
                const b64 = btoa(String.fromCharCode.apply(null, bytes));
                const resp = await fetch(base_url + '/analyze', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({data: b64})
                });
                const data = await resp.json();
                document.getElementById('analysis-result').innerHTML = 
                    '⚠️ Threat: ' + data.threat_level + '\n' +
                    '🎯 Type: ' + data.attack_type + '\n' +
                    '🔒 Confidence: ' + data.confidence.toFixed(3) + '\n' +
                    '⚡ Energy: ' + data.energy_harvested.toFixed(2) + '\n' +
                    '🛡️ Defense: ' + data.defense_power.toFixed(2);
                appendResponse('🔍 Analyzed packet → ' + data.threat_level);
                getStatus();
            } catch(e) {
                appendResponse('❌ Error: ' + e.message);
            }
        }
        
        function appendResponse(msg) {
            const el = document.getElementById('response');
            const time = new Date().toLocaleTimeString();
            el.innerHTML = '[' + time + '] ' + msg + '\n' + el.innerHTML;
            if (el.innerHTML.length > 5000) {
                el.innerHTML = el.innerHTML.substring(0, 5000);
            }
        }
        
        // Auto-refresh
        getStatus();
        setInterval(getStatus, 5000);
    </script>
</body>
</html>
'''

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'web':
        print("Serving web interface...")
        print("Open http://localhost:8888/ in your browser")
        print("(The C++ server must be running on port 8888)")
        print("\nTo serve the HTML, run: python3 -c \"$(cat sam_client_v2.py)\" web")
        import http.server
        import socketserver
        import tempfile
        import os
        
        # Create temp HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write(WEB_INTERFACE)
            html_file = f.name
        
        os.chdir(os.path.dirname(html_file))
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", 8080), handler) as httpd:
            print(f"Serving web interface at http://localhost:8080")
            print(f"Open this in your browser")
            print("Press Ctrl+C to stop")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
        
        os.unlink(html_file)
    else:
        # Command line client
        client = SamClient()
        print("Sam Client v2.0")
        print("Commands: status, teach <concept>, knowledge <concept>, list, state, analyze <text>, quit")
        
        while True:
            try:
                cmd = input("> ").strip()
                if cmd == 'quit':
                    break
                elif cmd == 'status':
                    print(json.dumps(client.status(), indent=2))
                elif cmd == 'list':
                    mastered = client.list_mastered()
                    unmastered = client.list_unmastered()
                    print("Mastered:")
                    for c in mastered:
                        print(f"  ✅ {c}")
                    print("Unmastered:")
                    for c in unmastered:
                        print(f"  ❌ {c}")
                elif cmd == 'state':
                    print(json.dumps(client.state(), indent=2))
                elif cmd.startswith('teach '):
                    concept = cmd[6:]
                    result = client.teach(concept)
                    print(f"Teach {concept}: {result}")
                elif cmd.startswith('knowledge '):
                    concept = cmd[10:]
                    result = client.knowledge(concept)
                    print(f"Knowledge: {result.get('knowledge', '')}")
                    print(f"Coherence: {result.get('coherence', 0)}")
                elif cmd.startswith('analyze '):
                    data = cmd[8:].encode()
                    result = client.analyze(data)
                    print(f"Analysis: {result}")
                else:
                    print("Unknown command")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")