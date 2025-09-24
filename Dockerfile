# ---------- base ----------
FROM ubuntu:24.04 AS base

ENV TZ=Asia/Jakarta \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_CACHE_DIR=/tmp/poetry_cache \
    POETRY_REQUESTS_TIMEOUT=1000

# timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# system deps
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev python3-venv pipx \
    ffmpeg libsm6 libxext6 \
    poppler-utils \
    curl wget tar zip git net-tools inetutils-ping pciutils vim \
    libssl-dev openssl make gcc \
    build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
    libreadline-dev libffi-dev libsqlite3-dev libbz2-dev \
    libxcb-cursor0 libxcb-xinerama0 \
    tesseract-ocr libtesseract-dev libleptonica-dev \
    tesseract-ocr-eng tesseract-ocr-ind \
    **swig** \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# ensure pipx-installed binaries are on PATH
ENV PATH="/root/.local/bin:${PATH}"

# infisical cli
RUN curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash \
    && apt-get update && apt-get install -y infisical \
    && rm -rf /var/lib/apt/lists/*

# ---------- deps ----------
FROM base AS dependencies
WORKDIR /app

# install Poetry isolated from system site-packages
RUN pipx install "poetry>=1.6"

# copy only files needed to resolve/install deps (better cache)
COPY pyproject.toml poetry.lock* ./

# install only the main (non-dev) dependency groups into an in-project venv at /app/.venv
RUN poetry install --no-root --only main --sync

# ---------- runtime ----------
FROM base AS runtime
WORKDIR /app

# copy the prebuilt virtualenv first (best cache hit)
COPY --from=dependencies /app/.venv /app/.venv

# make the venv the default Python
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="/app/.venv/bin:${PATH}"

# copy app code last for better rebuild times
COPY . .

# create config dir for mounts (root owns it by default)
RUN mkdir -p /app/config

# run as root (default)
USER root

# start the app (uses venv's python)
CMD ["python", "main.py"]