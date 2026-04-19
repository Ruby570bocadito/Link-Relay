# ☠️ Advanced APT C2 Framework (Ghost Infra)

![Build](https://img.shields.io/badge/Build-Native_PE32-brightgreen) ![Crypto](https://img.shields.io/badge/Encryption-AES_256_%2B_RSA_2048-blue) ![Status](https://img.shields.io/badge/Status-FUD_Evasive-red)

Un Framework de Comando y Control (C2) de grado Red Team diseñado para operaciones de auditoría sigilosas contra entornos corporativos. Evolucionado desde cero para operar exclusivamente en memoria RAM (Fileless), cifrar comunicaciones mediante criptografía matemática de nivel militar, y desplegarse multiescala en Linux y Windows.

## 🔥 Capacidades Arquitectónicas
*   **Criptografía Híbrida Efímera:** El servidor genera un KeyPair RSA de 2048-bits en vivo. Los agentes negocian dinámicamente un canal AES-CBC de 256-bits. No hay firmas criptográficas estáticas hardcodeadas.
*   **Evasión en Red TLS/SSL:** Túnel de comunicación vía HTTPS AdHoc. Interceptar el tráfico local solo arrojará firmas cifradas con certificados ilegibles.
*   **Malleable C2 & Jittering:** Camuflado de red estocástico. Aleatorización geométrica matemática para evitar detección de Beacons (Latencia aleatoria e Inyección Dinámica de User-Agents como Spotify o Mozilla).
*   **Terminal PTY Persistente Asíncrona:** Sesión continua multi-hilo emulada vía Ajax. Los túneles mantienen vivas las variables de entorno, los directorios en los que se encuentra (`cd`) y proveen interactividad nativa rápida de red (`0.5s` mode) para comandos robustos.
*   **Malware sin Dependencias (Native Builder):** Fábrica en Python cruzada que empaqueta todo el entorno (PyCryptoDome, Sockets SSL, TLS) y despliega FUD (Fully Undetectable) Windows `.EXE` o ELF genéricos mediante inyección en memoria.
*   **Dashboard Táctico Multiplayer:** Panel web con Flask para la gestión visual en Tiempo Real y un modo Fantasma (Jitter) para latencia a largo plazo sin despertar sospechas del Blue Team corporativo.

---

## 💻 Dashboard Táctico (Controles)
- `⚡ Real-Time PTY`: Eleva la agresividad del Beacon a latencia sub-segundo con Jitter a 0%. Genera una terminal persistente capaz de recibir y volcar outputs asíncronos rápidos (NMAPs, sudo, cat). (Advertencia: Demasiado ruido en la red corporativa).
- `👻 Ghost Mode` (Por Defecto): El agente duerme durante 5 minutos y despierta cíclicamente aleatorizando tiempos matemáticos para ocultarse de los analizadores de tráfico SOC.
- `Purge & Kill`: Envía directiva de auto-destrucción total. El agente mata sus túneles de persistencia en máquina víctima (`/run/registry` o `crontab`), limpia memoria RAM, elimina dependencias y el C2 lo elimina de la base `json` borrando la firma cibernética.

---

## 🛠 Entorno Autorizado
> [!WARNING]
> Todo el software contenido en este repositorio ha sido programado con fines educativos, de simulación de amenazas de tipo APT, e ingeniería inversa con autorización. Prohibido su uso fuera de entornos virtualizados de auditoría aislados. El autor y desarrollador no se hace responsable del mal uso de este arsenal de hacking.
