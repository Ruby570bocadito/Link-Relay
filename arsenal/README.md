# ⚔️ EL ARSENAL: Compilador Nativo (Dropper Factory)

Esta carpeta funciona como la "**Fábrica de Armamento**" de tu C2. Su único propósito es ingerir el código crudo Python (`agent_v2.py`) y escupir un archivo ejecutable (Payload) diseñado específicamente para la víctima, sin necesidad de que ésta tenga Python, PyCryptodome, ni ninguna dependencia instalada.

## ⚙️ ¿Cómo funciona por debajo?

El script principal de esta bóveda es **`c2_builder.py`**. Al ejecutarlo, realiza el siguiente Proceso Clandestino Dummificado:

1. **Lectura Base:** Coge el código fuente de tu `agent_v2.py` que yace en la carpeta raíz.
2. **Inyección Dinámica de IP (Doxing):** Busca la variable por defecto `C2_URL` y la reescribe en caliente con la IP y el Puerto reales que le hayas pasado por parámetro. Esto evita que tengas que andar cambiando el código a mano en el script real para cada ataque o red diferente.
3. **Ofuscación Temporal:** Escribe un archivo temporal `.py` con el código mutado.
4. **PyInstaller Factory:** Llama nativamente al compilador cruzado y le pasa las instrucciones críticas para el sigilo:
   *   `--onefile`: Todo empacado a presión en un solo fichero asfixiante que la víctima solo deba abrir 1 vez.
   *   `--windowed / --noconsole`: Impide categóricamente que se muestre una terminal negra en Windows. La ejecución será invisible ("Silent Crash" garantizado en caso de fallo y "Ghost Daemon" en caso de éxito).
   *   `--clean`: Borra cachés anteriores para asegurar entropía pura en el binario sin heurísticas predecibles.
5. **Drop & Extract:** Elimina automáticamente todas las pruebas del compilador temporal (`build/`, `__pycache__`) y traslada el `.exe` final a la carpeta matriz `transfers/C2_Automated_Payload.exe`.

---

## 🛠️ Modos de Uso

Abre una consola, posiciónate en la carpeta RAÍZ del proyecto (`C2_Project/`) o dentro del propio `./arsenal` y ejecuta el compilador indicando a AL OBJETIVO A DONDE QUIERES QUE LLAME:

```bash
# Estando dentro de la carpeta C2_Project/:
python arsenal/c2_builder.py <IP_DEL_C2> <PUERTO_DEL_C2>

# Ejemplo Mágico (Si tu C2 corre en tu casa bajo la IP Local 192.168.1.132):
python arsenal/c2_builder.py 192.168.1.132 5000
```

### 💡 Secretos del Compilador
> [!TIP]
> **Compatibilidad Cruzada Matemática**: El compilador utilizará el Sistema Operativo que TU estés usando en este momento. 
> - Si corres el comando anterior **desde Windows**, te generará un `C2_Automated_Payload.exe` para destruir máquinas Windows.
> - Si pasas la carpeta `C2_Project` a tu **Kali Linux** y corres el comando ahí, PyInstaller generará un Elf-Binary sin extensión capaz de destruir servidores Ubuntu o Debian nativamente.
