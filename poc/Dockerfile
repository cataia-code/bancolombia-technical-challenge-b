# Imagen del servicio de analisis (FastAPI). Multi-stage minimalista.
FROM python:3.12-slim

WORKDIR /app

# Instala dependencias primero (mejor cache de capas).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el codigo y los datos de ejemplo.
COPY src/ ./src/
COPY data/ ./data/

ENV PYTHONPATH=/app/src
ENV TASKBOT_REPORTS_DIR=/app/reports
EXPOSE 8000

# Healthcheck para que n8n/compose sepan cuando esta listo.
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "taskbot_advisor.interface.api:app", "--host", "0.0.0.0", "--port", "8000"]
