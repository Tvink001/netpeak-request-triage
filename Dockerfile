# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependency layer — cached unless pyproject.toml changes. A stub package lets
# `pip install -e .` resolve metadata without the real source, so editing
# triage/ later does not reinstall the dependency tree.
COPY pyproject.toml README.md ./
RUN mkdir -p triage \
 && printf '"""triage package."""\n' > triage/__init__.py \
 && pip install --upgrade pip \
 && pip install -e .

# Real source + the sample inbox (so `docker run <image>` works out of the box).
COPY triage/ ./triage/
COPY test-data/ ./test-data/

ENTRYPOINT ["python", "-m", "triage"]
CMD ["test-data/input_requests.csv"]
