FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY fpt_customer_chatbot_api/requirements-docker.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY fpt_customer_chatbot_api ./fpt_customer_chatbot_api

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"

CMD ["uvicorn", "fpt_customer_chatbot_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
