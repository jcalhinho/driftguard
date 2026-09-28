FROM python:3.12-slim

WORKDIR /app

# Engine + rules first (cached layer), then the web service.
COPY pyproject.toml README.md LICENSE ./
COPY driftguard ./driftguard
RUN pip install --no-cache-dir ".[app]"

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
