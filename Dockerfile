FROM python:3.11-slim

# Evitar que python escriba bytecode y forzar output sin buffer
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Cambiar al directorio de trabajo
WORKDIR /opt/c2_server

# Instalar dependencias del sistema requeridas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar configuración e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt Flask prompt_toolkit

# Copiar el código fuente del C2
COPY . .

# Crear volúmenes para persistencia
VOLUME ["/opt/c2_server/logs", "/opt/c2_server/transfers", "/opt/c2_server/c2_database.json"]

# Exponer el panel Web Frontend
EXPOSE 5000

# Punto de entrada predeterminado
CMD ["python", "c2_teamserver.py"]
