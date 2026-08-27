ARG PYTHON_VER="3.11"
FROM python:${PYTHON_VER}-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc pkg-config && \
    rm -rf /var/lib/apt/lists/* && \
    python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY vsem_fms/requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

FROM python:${PYTHON_VER}-slim

ARG _USER=appuser
ARG _GROUP=appgroup

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd "${_GROUP}" && \
    useradd --no-log-init -r --no-create-home -g "${_GROUP}" "${_USER}"

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app"

COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY vsem_fms /app/vsem_fms

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${SERVER_PORT:-5000}/api/v1/ping" || exit 1

CMD ["/bin/bash", "/app/vsem_fms/commands/entrypoint.sh"]
