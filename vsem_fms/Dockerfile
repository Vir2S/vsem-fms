ARG PYTHON_VER="3.11"
FROM python:${PYTHON_VER}-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential gcc pkg-config \
    mariadb-client && \
    apt-get clean -y && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*  && \
    python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH="/app/vsem_fms"

WORKDIR /app
COPY vsem_fms/requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt --no-cache-dir

FROM python:${PYTHON_VER}-slim

ARG _USER=appuser
ARG _GROUP=appgroup

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    mariadb-client curl && \
    apt-get clean -y && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd ${_GROUP} && useradd --no-log-init -r --no-create-home -G ${_GROUP} ${_USER}

ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH="/app/vsem_fms"
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY vsem_fms /app/vsem_fms

CMD ["/bin/bash", "/app/vsem_fms/commands/entrypoint.sh"]