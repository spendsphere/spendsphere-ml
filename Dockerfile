FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     git     && rm -rf /var/lib/apt/lists/*

RUN pip install "poetry>=1.8.0" && poetry config virtualenvs.create false

COPY . /app
RUN poetry install --no-interaction --no-ansi
RUN poetry add pydantic@2.8.2

CMD ["python", "src/main.py", "--demo"]
