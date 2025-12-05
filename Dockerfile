FROM python:3.12-slim

WORKDIR /app

ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_MODELS=/root/.ollama/models

# --- System deps ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- Install Poetry ---
RUN pip install "poetry>=1.8.0" && poetry config virtualenvs.create false

# --- Install Ollama ---
RUN curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service manually to pull models
RUN ollama serve & \
    sleep 4 && \
    ollama pull qwen3:14b && \
    ollama pull qwen3-vl:4b && \
    sleep 2

# --- Python project ---
COPY . /app
RUN poetry install --no-interaction --no-ansi
RUN poetry add pydantic@2.8.2

EXPOSE 11434

CMD ["python", "src/main.py", "--demo"]
