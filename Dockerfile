FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ src/
COPY config/ config/
COPY knowledge/ knowledge/
COPY agents/ agents/

RUN pip install --no-cache-dir ".[dspy]"

EXPOSE 8000

CMD ["uvicorn", "pylon.main:app", "--host", "0.0.0.0", "--port", "8000"]
