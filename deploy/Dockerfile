FROM python:3.12-slim

WORKDIR /app

# Engine + rules first (cached layer), then the web service.
COPY pyproject.toml README.md LICENSE ./
COPY driftguard ./driftguard
# chmod: host files may be 0600 and COPY keeps modes; the service user must read them.
RUN chmod -R a+rX /app && pip install --no-cache-dir ".[app]" && rm -rf build *.egg-info

COPY app ./app
COPY deploy/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod -R a+rX /app/app && useradd --system --no-create-home --shell /usr/sbin/nologin driftguard

EXPOSE 8000

ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
