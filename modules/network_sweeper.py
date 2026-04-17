import socket
import ipaddress
import threading
from queue import Queue
import urllib.request
import base64

DEFAULT_CREDS = [
    ("admin", "admin"), 
    ("admin", "12345"), 
    ("admin", "123456"), 
    ("root", "root"), 
    ("admin", "")
]

def try_http_auth(ip, port):
    """Prueba rápida de contraseñas por defecto en HTTP Basic Auth"""
    for user, pwd in DEFAULT_CREDS:
        try:
            url = f"http://{ip}:{port}/"
            req = urllib.request.Request(url)
            auth_str = f"{user}:{pwd}"
            b64_auth = base64.b64encode(auth_str.encode('utf-8')).decode('utf-8')
            req.add_header("Authorization", f"Basic {b64_auth}")
            response = urllib.request.urlopen(req, timeout=1.0)
            if response.getcode() in [200, 301, 302]:
                return f"http://{user}:{pwd}@{ip}:{port}/ (¡Credenciales Válidas!)"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                continue # Probar siguiente password
            return f"http://{ip}:{port}/ (No requiere auth o estado {e.code})"
        except Exception:
            continue
    return f"http://{ip}:{port}/ (Requiere auth desconocida)"

class NetworkSweeper:
    """Módulo para descubrir de forma silenciosa e interna cámaras, dispositivos IoT y Servidores Informáticos"""
    def __init__(self, ports=None, timeout=0.5, threads=50):
        # Puertos comunes de CCTV, RTSP, e interfaces Web de IoT + Puertos IT
        self.ports = ports if ports else [21, 22, 80, 443, 445, 554, 3389, 8000, 8080, 8554]
        self.timeout = timeout
        self.threads_count = threads
        self.results = []
        self.queue = Queue()
        self.lock = threading.Lock()

    def _scan_target(self):
        while not self.queue.empty():
            ip_port = self.queue.get()
            ip = ip_port[0]
            port = ip_port[1]
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(self.timeout)
                result = s.connect_ex((ip, port))
                if result == 0:
                    with self.lock:
                        found = False
                        for entry in self.results:
                            if entry['ip'] == ip:
                                entry['ports'].append(port)
                                found = True
                                break
                        if not found:
                            self.results.append({'ip': ip, 'ports': [port]})
                s.close()
            except Exception:
                pass
            finally:
                self.queue.task_done()

    def sweep(self, target_subnet: str) -> list:
        """Escanea una subred (ej: 192.168.1.0/24) buscando dispositivos tipo cámara."""
        self.results = []
        try:
            network = ipaddress.ip_network(target_subnet, strict=False)
            hosts = list(network.hosts())
            
            # Limitar a subredes pequeñas para no bloquear el agente
            if len(hosts) > 1024:
                return [{"error": "La subred es demasiado grande (máximo /22 o 1024 hosts recomendados)."}]

            # Llenar la cola
            for host in hosts:
                for port in self.ports:
                    self.queue.put((str(host), port))

            threads = []
            for _ in range(self.threads_count):
                t = threading.Thread(target=self._scan_target)
                t.daemon = True
                t.start()
                threads.append(t)

            self.queue.join()
            return self.results
            
        except ValueError:
            return [{"error": f"Formato de red inválido: {target_subnet}. Usa formato CIDR (ej. 192.168.1.0/24)."}]
        except Exception as e:
            return [{"error": str(e)}]

def run_sweep(subnet: str) -> str:
    """Helper para ser invocado desde agent.py"""
    sweeper = NetworkSweeper()
    discovered = sweeper.sweep(subnet)
    
    if not discovered:
        return "[*] Escaneo finalizado. No se encontraron dispositivos en esos puertos."
    if "error" in discovered[0]:
        return f"[-] Error en escaneo: {discovered[0]['error']}"
        
    output = "[+] Dispositivos IT / Cámaras potenciales descubiertos:\n"
    for r in discovered:
        ip = r['ip']
        ports_str = ", ".join([str(p) for p in r['ports']])
        output += f"\n[+] HOST: {ip} | Puertos: {ports_str}\n"
        
        # Recon IT Corporativo
        for p in r['ports']:
            if p == 445: output += f"    -> [SMB/445] Servidor de Archivos o AD (Objetivo de Movimiento Lateral)\n"
            elif p == 3389: output += f"    -> [RDP/3389] Remote Desktop Abierto\n"
            elif p == 22: output += f"    -> [SSH/22] Servidor Linux detectado\n"
            elif p == 21: output += f"    -> [FTP/21] Servidor de Archivos detectado\n"
            
            # Recon Web & IoT
            if p in [80, 8080, 8000]:
                auth_result = try_http_auth(ip, p)
                output += f"    -> [HTTP/{p}] Sugerencia: {auth_result}\n"
            elif p in [554, 8554]:
                output += f"    -> [RTSP/{p}] Cámara de Seguridad. Prueba tu fuerza bruta.\n"
        
    return output
