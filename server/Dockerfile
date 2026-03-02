FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r challanai && useradd -r -g challanai -m challanai

WORKDIR /app

COPY server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt

COPY src/ /app/src/
COPY server/ /app/server/
COPY config.yaml /app/config.yaml

RUN chown -R challanai:challanai /app /tmp

USER challanai

EXPOSE 8080

CMD ["uvicorn", "server.api:app", "--host", "0.0.0.0", "--port", "8080"]
