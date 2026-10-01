# ===============================
#   Base Image
# ===============================
ARG PYTHON_VERSION=3.12.3-bookworm
FROM python:${PYTHON_VERSION} as base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYDEVD_DISABLE_FILE_VALIDATION=1

WORKDIR /app/backend


# ===============================
#   Builder Stage
# ===============================
FROM base as builder

# Install system dependencies with GDAL from Debian backports
RUN set -eux; \
    echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/backports.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libpq-dev \
        libgeos-dev \
        libproj-dev \
        libopenblas-dev \
        libjpeg-dev \
        libtiff-dev \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
        netcat-traditional \
        -t bookworm-backports \
        gdal-bin \
        postgresql-client \
        libgdal-dev; \
    ldconfig; \
    gdal-config --version; \
    rm -rf /var/lib/apt/lists/*

# Install Python deps (match GDAL version)
RUN GDAL_VERSION=$(gdal-config --version | cut -d. -f1-2); \
    pip install --upgrade pip && \
    pip config set global.index-url https://pypi.org/simple && \
    pip install --no-cache-dir --default-timeout=400 \ GDAL==${GDAL_VERSION}.*

# Copy and build wheels
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt


# ===============================
#   Final Runtime Stage
# ===============================
FROM base

# Install runtime dependencies
RUN set -eux; \
    echo "deb http://deb.debian.org/debian bookworm-backports main" > /etc/apt/sources.list.d/backports.list; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libpq5 \
        libjpeg62-turbo \
        libtiff6 \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
        netcat-traditional \
        postgresql-client; \
    apt-get install -y --no-install-recommends -t bookworm-backports \
        gdal-bin \
        libgdal-dev \
        libgeos-dev \
        libproj-dev; \
    ldconfig; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

# Install prebuilt wheels from builder
COPY --from=builder /wheels /wheels
RUN pip install --no-index --find-links=/wheels /wheels/* && rm -rf /wheels

# Copy Firebase credentials (must live inside apps/backend/)
COPY --chown=app:app firebase-credentials.json /app/backend/firebase-credentials.json

# Create non-root user
RUN groupadd -g 1001 app && \
    useradd -u 1001 -g app -d /app/backend -s /bin/bash app && \
    mkdir -p /app/backend/static /app/backend/media && \
    chown -R app:app /app/backend

# Copy app source (context is already ./apps/backend)
COPY --chown=app:app entrypoint.prod.sh /app/backend/
COPY --chown=app:app . /app/backend/
RUN chmod +x /app/backend/entrypoint.prod.sh

USER app

ENTRYPOINT ["/app/backend/entrypoint.prod.sh"]
