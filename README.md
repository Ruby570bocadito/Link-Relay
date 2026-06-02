<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=0,2,3,6&height=200&section=header&text=Link-Relay&fontSize=60&fontAlignY=38&desc=C2+Framework+%7C+Post-Explotaci%C3%B3n+%7C+Visi%C3%B3n+por+IA&descAlignY=55&descSize=18&animation=fadeIn" width="100%"/>
</p>

<p align="center">
  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=20&pause=1000&color=00F7FF&center=true&vCenter=true&width=700&lines=C2+Framework+completo+con+Panel+Web+y+Visi%C3%B3n+por+IA;Implant+fileless+con+cifrado+AES+%2B+RSA;Anti-sandbox+%7C+AMSI+bypass+%7C+Persistencia+autom%C3%A1tica;SOCKS5+pivot+%7C+Keylogger+%7C+Inyecci%C3%B3n+fileless+en+RAM" alt="Typing SVG" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-00f7ff?style=for-the-badge&logo=python&logoColor=white&labelColor=0d1117" />
  <img src="https://img.shields.io/badge/C2-Framework-FF4500?style=for-the-badge&logo=matrix&logoColor=white&labelColor=0d1117" />
  <img src="https://img.shields.io/badge/License-MIT-00f7ff?style=for-the-badge&logo=opensourceinitiative&logoColor=white&labelColor=0d1117" />
  <br />
  <img src="https://img.shields.io/github/last-commit/Ruby570bocadito/Link-Relay?style=flat-square&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/stars/Ruby570bocadito/Link-Relay?style=flat-square&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/github/repo-size/Ruby570bocadito/Link-Relay?style=flat-square&labelColor=0d1117&color=00f7ff" />
  <img src="https://img.shields.io/badge/Platform-Windows_%7C_Linux-FFD700?style=flat-square&labelColor=0d1117" />
</p>

---

## 🔥 ¿Qué es Link-Relay?

**Link-Relay** es un **Framework C2 (Command & Control) completo** con:
- 🤖 **Implant fileless** con cifrado RSA+AES, anti-sandbox, AMSI bypass
- 🖥️ **Panel Web** con dashboard de beacons y control de agentes
- 🎮 **Consola interactiva** con autocompletado
- 🧩 **Post-explotación**: keylogger, captura de pantalla, network sweep, UAC bypass
- 🔀 **SOCKS5 pivot** para rutear tráfico a través del agente infectado
- 🤖 **Visión por IA (YOLOv8)**: reconocimiento de objetos en tiempo real desde cámaras IoT
- 🏗️ **Builder** para compilar payloads nativos Windows (.exe) sin dependencias

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   ┌─────────────┐     ┌──────────────────┐     ┌────────────────┐   │
│   │  Operador   │────►│   C2 Server      │◄────│   Agente       │   │
│   │  (Consola/  │     │  Flask Web + API  │     │  (Fileless)    │   │
│   │   Web UI)   │◄────│  + SOCKS5 Router  │────►│  AES+RSA       │   │
│   └─────────────┘     └──────────────────┘     │  Anti-Sandbox  │   │
│                                                  │  AMSI Patch    │   │
│                                                  │  Keylogger     │   │
│                                                  │  PTY Shell     │   │
│                                                  │  Módulos       │   │
│                                                  └────────────────┘   │
│                                                         │             │
│                                                         ▼             │
│                                                  ┌────────────────┐   │
│                                                  │   Módulos      │   │
│                                                  │  (fileless RAM)│   │
│                                                  └────────────────┘   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### Requisitos

```bash
# Python 3.10+
pip install -r requirements.txt
```

### 1. Iniciar el TeamServer (consola)

```bash
python c2_teamserver.py
```

Esto levanta:
- Panel web en `https://0.0.0.0:5000` (login: `admin` / `c2admin2026`)
- API REST para beacons
- Router SOCKS5 en `127.0.0.1:1080`

### 2. (Alternativa) Servidor HTTP clásico

```bash
python server_v2.py
```

Consola interactiva con autocompletado (`TAB`).

### 3. Generar payload (agente)

```bash
cd arsenal
python c2_builder.py <TU_IP> <PUERTO>
# Ej: python c2_builder.py 192.168.1.100 5000
```

Esto genera un `agent_v2.exe` en `arsenal/dist/` listo para desplegar.

### 4. Ejecutar el agente directo (modo dev)

Edita `C2_URL` en `agent_v2.py` y ejecuta:

```bash
python agent_v2.py
```

---

## 🏗️ Estructura del Proyecto

```
Link-Relay/
├── c2_teamserver.py            # TeamServer Flask (panel web + API + SOCKS5)
├── server_v2.py                # Servidor HTTP con consola interactiva
├── agent_v2.py                 # Implant C2 (fileless, anti-sandbox, cifrado)
├── requirements.txt            # Dependencias Python
├── Dockerfile                  # Build Docker del servidor C2
├── OPERACIONES_RED_TEAM.md     # Manual de operaciones (español)
├── .gitignore
│
├── arsenal/                    # Herramientas de compilación y ataque
│   ├── c2_builder.py           # Compila agent_v2 a .exe con PyInstaller
│   ├── dropper.py              # Stage1 dropper
│   ├── iot_sniper.py           # Herramienta IoT
│   └── README.md
│
├── modules/                    # Módulos post-explotación (fileless)
│   ├── __init__.py
│   ├── crypto.py               # Cifrado
│   ├── keylogger.py             # Keylogging
│   ├── network_sweeper.py       # Escaneo de red
│   ├── screenshot.py            # Captura de pantalla
│   ├── stream_capture.py        # Captura de video
│   └── uac_bypass.py            # Bypass de UAC (Windows)
│
├── templates/                  # Web dashboard (Flask)
│   ├── login.html
│   └── dashboard.html
│
├── static/                     # Assets del panel web
│   ├── css/
│   └── js/
│
├── docs/
│   └── IOT_VISION_C2_MANUAL.md # Manual de visión IoT
│
├── logs/                       # Logs (generado)
├── transfers/                  # Archivos transferidos (generado)
└── c2_database.json            # Base de datos de beacons (generado)
```

---

## 🎯 Características

### Implant (Agent)

| Característica | Descripción |
|---|---|
| 🔐 **Cifrado Híbrido RSA+AES** | Handshake RSA-2048, sesiones con clave AES única |
| 🛡️ **Anti-Sandbox** | Detecta entornos de análisis (poca RAM, procesos, usuarios) |
| 💉 **AMSI Bypass** | Parchea `AmsiScanBuffer` en memoria (Windows) |
| 🔄 **Persistencia Automática** | Run Key + Scheduled Task en primer arranque |
| ⌨️ **Keylogger Nativo** | Captura teclas vía `GetAsyncKeyState` |
| 🖥️ **PTY Shell Persistente** | Shell interactiva asíncrona |
| 🔀 **SOCKS5 Proxy** | Túnel TCP para pivoting |
| 🧩 **Inyección Fileless** | Carga módulos Python directamente en RAM sin tocar disco |
| 📷 **Captura de Visión** | Webcam / pantalla → YOLOv8 para detección de objetos |
| 🎭 **Ofuscación de Tráfico** | User-Agent aleatorio, headers tipo nginx, jitter |

### TeamServer

| Característica | Descripción |
|---|---|
| 🌐 **Panel Web** | Dashboard con login, lista de beacons, cola de tareas |
| 🎮 **Consola Interactiva** | Autocompletado con `prompt_toolkit` |
| 📋 **Cola de Tareas** | Encola comandos para ejecución remota |
| 🔀 **SOCKS5 Router** | Enruta tráfico de proxychains a través del agente |
| 🤖 **Visión por IA** | Procesa frames con YOLOv8 (ultralytics) |
| 💾 **Persistencia de Estado** | Base de datos JSON con beacons activos |

### Módulos Post-Explotación

| Módulo | Descripción |
|---|---|
| `network_sweeper` | Escanea redes internas desde el agente |
| `screenshot` | Captura pantalla del escritorio remoto |
| `stream_capture` | Captura video de cámara/webcam |
| `keylogger` | Logging de teclas (versión PyPi) |
| `uac_bypass` | Escalada de privilegios UAC (Windows) |
| `crypto` | Utilidades criptográficas |

---

## 🖥️ API Endpoints

### C2 API (agentes)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/v2/get_cert` | Descarga la clave pública RSA del servidor |
| `POST` | `/api/v2/handshake` | Registro inicial del agente (handshake RSA+AES) |
| `GET` | `/api/v2/telemetry` | Check-in del beacon, recibe tareas pendientes |
| `POST` | `/api/v2/update` | Envía resultados de tareas al servidor |
| `GET` | `/stage2` | Descarga el agent_v2.py completo (stage2) |

### Admin API (panel web)

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| `GET` | `/login` | Página de login | None |
| `POST` | `/login` | Autenticación | None |
| `GET` | `/admin/dashboard` | Panel de control | Sesión |
| `GET` | `/api/admin/beacons` | Lista de beacons activos | Sesión |
| `POST` | `/api/admin/tasks` | Encola tarea en un beacon | Sesión |
| `GET` | `/api/admin/results` | Obtiene resultados de tareas | Sesión |

---

## 🖥️ Uso del TeamServer (Consola)

```bash
python server_v2.py
```

Comandos de la consola interactiva:

| Comando | Descripción |
|---------|-------------|
| `beacons` | Listar beacons activos |
| `use <id>` | Interactuar con un beacon específico |
| `shell <cmd>` | Ejecutar comando en el beacon |
| `inject <módulo>` | Inyectar módulo fileless (sweep, keylogger, etc.) |
| `sweep` | Ejecutar network sweeper |
| `watch` | Activar vigilancia por cámara |
| `sleep <seg>` | Cambiar intervalo de beacon |
| `persist` | Activar persistencia |
| `elevate` | Intentar escalada de privilegios |
| `results` | Ver resultados de tareas |
| `generate` | Generar nuevo payload |
| `kill` | Terminar el beacon y purgarlo |
| `exit` | Salir |

---

## 🤖 Visión por IA (YOLOv8)

El C2 puede procesar frames de cámara/webcam usando **YOLOv8** (ultralytics) para detectar objetos en tiempo real:

1. El agente captura un frame de la cámara
2. Lo envía cifrado al servidor
3. El servidor procesa con YOLOv8 y devuelve detecciones
4. Las imágenes con detecciones se guardan en `transfers/detections/`

> ⚠️ El modelo `yolov8n.pt` se descarga automáticamente con ultralytics la primera vez.

---

## 🔧 Personalización

### Variables de entorno (recomendado)

```bash
export C2_HOST="0.0.0.0"
export C2_PORT="5000"
export C2_PASSWORD="tu_password_segura"
```

### Configuración hardcodeada (editar código)

En `agent_v2.py`:
```python
C2_URL = "https://127.0.0.1:5000"       # URL del servidor C2
BEACON_INTERVAL = 5                       # Segundos entre check-ins
JITTER = 0.3                              # Jitter aleatorio
```

En `server_v2.py`:
```python
HOST = '0.0.0.0'
PORT = 4444
```

---

## 🐳 Docker

```bash
# Construir y ejecutar el servidor C2
docker build -t link-relay-c2 .
docker run -d -p 5000:5000 -v ./logs:/opt/c2_server/logs -v ./transfers:/opt/c2_server/transfers link-relay-c2
```

---

## 🛡️ Aviso Legal

Link-Relay está diseñado **exclusivamente para pruebas de seguridad autorizadas y entornos controlados**. 

- ✅ Obtén permiso explícito por escrito antes de usar
- ✅ Usa solo en máquinas que te pertenezcan o con autorización
- ❌ El uso no autorizado es ilegal y constituye un delito

> **Los autores no se responsabilizan del mal uso de esta herramienta.**

---

## 📄 Licencia

[MIT](LICENSE) © 2025 [Ruby570bocadito](https://github.com/Ruby570bocadito)

---

<p align="center">
  <sub>C2 Framework · Post-Explotación · Visión por IA</sub>
</p>
