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
    && rm -rf /var/lib/apt/lists/*

# --- Poetry ---
RUN pip install "poetry>=1.8.0" && poetry config virtualenvs.create false

# --- Copy only dependency files and install dependencies ---
COPY pyproject.toml poetry.lock* /app/
RUN poetry install --no-interaction --no-ansi --no-root

# --- Copy full project ---
COPY . /app

# --- Optional: install specific packages if needed ---
# RUN poetry add pydantic@2.8.2  # if not in pyproject.toml

# --- Ollama environment ---
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models

# --- Expose port if needed for Ollama API ---
EXPOSE 11434
