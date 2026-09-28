FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
COPY app/requirements.txt ./app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r app/requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
