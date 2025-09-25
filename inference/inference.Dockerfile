# ---------- base ----------
FROM ubuntu:22.04 AS base

ENV TZ=Asia/Jakarta

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

WORKDIR /app

RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install --upgrade pipx \
    && python3 -m pipx ensurepath || true

RUN pipx install uv || true

COPY pyproject.toml uv.lock* ./
RUN if command -v uv >/dev/null 2>&1; then uv sync || true; else echo "uv not found; skipping uv sync"; fi

COPY . .

USER root
CMD ["uv", "run", "python", "main.py"]
