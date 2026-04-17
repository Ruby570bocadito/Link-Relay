# Manual Operativo: Módulos IoT y Visión en C2

Este documento es una guía táctica sobre cómo utilizar las capacidades avanzadas de descubrimiento y explotación integradas en el framework C2. Estas herramientas permiten saltar de una red a otra (Pivoting), interceptar flujos de vídeo de cámaras expuestas (IoT/CCTV), y procesarlas mediante Inteligencia Artificial.

---

## 1. Arquitectura de Despliegue (Topología)

*   **Punto A (Servidor C2 / Atacante):** Es tu equipo principal (`server.py`). Almacena los logs, tiene la potencia computacional para correr YOLOv8 y procesa la información de forma centralizada.
*   **Punto B (Agente / Víctima):** Es la máquina comprometida (`agent.py`). Actúa como puente o proxy silencioso hacia redes inaccesibles desde internet.
*   **Punto C (Objetivo IoT):** Son las webcams, cámaras IP o dispositivos ESP32 expuestos dentro de la misma red local que el Punto B.

---

## 2. Fase de Enumeración (Comando `sweep`)

Una vez que has obtenido una sesión C2 en el equipo víctima, necesitas conocer su entorno.

### Ejecución
```bash
[C2 - Sesión 0]> sweep 192.168.1.0/24
```

### ¿Qué ocurre por debajo?
1.  **Escaneo Básico:** El Agente sondea todas las IP de la subred especificada.
2.  **Identificación de Puertos:** Busca servicios en los puertos `80`, `443`, `8080`, `8000`, `554`, `8554`.
3.  **Fuerza Bruta de Credenciales (Automática):** 
    *   Si encuentra un servicio **HTTP (ej. panel web de una cámara)**, intentará una rápida inyección de credenciales por defecto (admin:admin, etc.) usando el formato `Authorization: Basic...`
    *   Si encuentra un servicio **RTSP (vídeo crudo)**, te listará variaciones de la URL para facilitar el acceso rápido.
4.  **Respuesta:** El servidor te imprimirá exactamente la URL que tienes que usar para atacarlo visualmente.

---

## 3. Fase de Explotación Silenciosa (Comando `watch`)

Una vez la cámara ha sido identificada por el escáner y tienes una URL candidata, comienzas la extracción de inteligencia.

### Ejecución
```bash
[C2 - Sesión 0]> watch rtsp://admin:12345@192.168.1.50:554/live
```
*(Tip: También puedes usar `watch 0` para encender la webcam local del portátil de la víctima encubiertamente).*

### ¿Qué ocurre por debajo?
1.  **Interceptación (Agente):** El Agente se conecta a la cámara RTSP que le indicaste sin descargar el vídeo completo (el streaming constante sería un gran Indicador de Compromiso - IoC). 
2.  **Snapshot:** El Agente extrae un único **fotograma clave**, lo comprime y codifica en Base64. Cierra la conexión de inmediato.
3.  **Filtración Evasiva:** Envía ese "string" inofensivo de texto a través de tu túnel C2 encriptado por AES-256.

---

## 4. Fase de Inteligencia Artificial (Server-Side)

### ¿Qué ocurre por debajo?
1.  **Reconstrucción:** Tu PC Central (`server.py`) recibe el paquete Base64 y pinta de nuevo la imagen extraída de la red del cliente.
2.  **Inferencia YOLOv8:** Automáticamente "alimenta" la imagen al modelo pre-entrenado de Ultralytics YOLOv8. El modelo detectará: Personas, teléfonos, vehículos, etc.
3.  **Alerta:** Aparecerá un aviso visual en tu terminal del servidor con los niveles de confianza del hallazgo:
    ```
    [!!] YOLO DETECTÓ (rtsp://192...): person(0.85), laptop(0.60)
    ```
4.  **Guardado:** La imagen con las "cajas delimitadoras" (bounding boxes) dibujadas en rojo se almacenará automáticamente en:
    *   `transfers/detections/vision_s0_2024...jpg`

Este ciclo te permite auditar instalaciones enteras de videovigilancia corporativa bajo estrictas pruebas de intrusión y OPSEC validado.

---

## 5. Fase de Evasión Avanzada y Supervivencia (OPSEC Nivel Red Team)

Para mimetizar tu actividad con un atacante de nivel *Estado-Nación* (APT), la versión V2 del C2 incorpora herramientas de control de tiempos (Jittering) y auto-borrado forense completo.

### 5.1. Control Dinámico de Tiempos (`sleep`)
Los sistemas de detección de intrusos (IDS) cazan conexiones cíclicas "perfectas". Si se manda un ping cada 5.0 segundos exactos, te cazarán.
Para operaciones largas, debes adormecer al malware y alterar su Jitter aleatorio:
```bash
(C2) [ID]> sleep 3600 0.5
```
*   **3600**: El tiempo base de cada llamada HTTP baja a 3600 segundos (1 hora).
*   **0.5**: Añade un +- 50% de aleatoriedad. El implante llamará a casa en intervalos aleatorios de entre 30 minutos y 90 minutos.

### 5.2. Borrado de Artefactos Forenses (`kill`)
Si la operación falla, pierdes el equipo C2, o terminas la auditoría, **jamás** debe quedar rastro en el cliente de tu persistencia ni tu binario.
```bash
(C2) [ID]> kill
```
Al invocar esto:
1.  El malware limpia inmediatamente la rama del Registro de Windows (`HKCU\...\Run`) eliminando su autoinicio.
2.  Desata una cadena temporal en segundo plano (vía cmd ping timeout) y suicida su propio proceso `sys.exit(0)`.
3.  Esa cadena temporal borra físicamente el archivo `agent_v2.py` del disco duro del objetivo mientras ya no está corriendo.
