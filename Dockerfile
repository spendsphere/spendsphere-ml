# Use minimal Python 3.12
FROM python:3.12-slim

WORKDIR /app

# --- Set PYTHONPATH for correct imports ---
ENV PYTHONPATH=/app

# --- System dependencies ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# --- Poetry ---
RUN pip install "poetry>=1.8.0" && poetry config virtualenvs.create false

# --- Copy only dependency files and install dependencies ---
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-interaction --no-ansi --no-root

# --- Copy full project ---
COPY . /app

# --- Ollama environment ---
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models

# --- Expose port for Ollama API ---
EXPOSE 11434

# --- Install Ollama CLI ---
RUN curl -sSfL https://ollama.com/install.sh | bash

# --- Download required models (example) ---
RUN ollama pull deepseek-ocr:latest
RUN ollama pull qwen3:0.6b

# --- Entrypoint: run Ollama in background and then ML worker ---
CMD ["sh", "-c", "\
    ollama serve --host $OLLAMA_HOST & \
    poetry run python src/main.py --demo \
"]
