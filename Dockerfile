FROM node:22-bookworm-slim AS frontend
WORKDIR /build/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
ENV VITE_API_BASE_URL=/api/v1
ENV VITE_ORBIT_SHOWCASE=true
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ORBIT_SHOWCASE=true SERVE_FRONTEND=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
COPY ml/requirements-water.lock /app/ml/requirements-water.lock
RUN pip install --no-cache-dir -r ml/requirements-water.lock
COPY backend/app /app/backend/app
COPY ml/water /app/ml/water
COPY ml/models/water /app/ml/models/water
COPY deployment/water /app/deployment/water
COPY data/demo /app/data/demo
COPY --from=frontend /build/web/dist /app/web/dist
RUN useradd --create-home orbit
USER orbit
WORKDIR /app/backend
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
