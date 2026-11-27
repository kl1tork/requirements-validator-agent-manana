# Для любого хостинга с Docker (Railway, Fly.io, свой сервер).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY reqval reqval
COPY assets assets
ENV MANANA_HOST=0.0.0.0 PORT=8765 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "-m", "reqval.web"]
