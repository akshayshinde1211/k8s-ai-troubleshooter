FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /home/app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY troubleshooter ./troubleshooter

USER app

ENTRYPOINT ["python", "main.py"]
