FROM python:3.13-slim AS dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --target /opt/function -r requirements.txt
COPY training_backend /opt/function/training_backend

FROM python:3.13-slim
WORKDIR /app
COPY --from=dependencies /opt/function /opt/function
ENV PYTHONPATH=/app:/opt/function PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN pip install --no-cache-dir pytest==8.4.2
COPY scripts scripts
COPY tests tests
COPY pytest.ini .
CMD ["python", "-m", "scripts.provision"]

