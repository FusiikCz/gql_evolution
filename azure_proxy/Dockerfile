# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.11-slim AS prepare

# instalace curl, aby bylo mozne zprovoznit standardni healthcheck
RUN apt update && apt install curl -y && rm -rf /var/cache/apk/*

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
WORKDIR /app
COPY azure_proxy/requirements.txt /app/requirements.txt
RUN python -m pip install -r /app/requirements.txt

COPY azure_proxy /app/azure_proxy
COPY src /app/src

ENV PYTHONPATH=/app

RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
#CMD ["gunicorn", "--reload=True", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "300", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
WORKDIR /app
CMD ["uvicorn", "azure_proxy.main:app", "--host", "0.0.0.0", "--port", "8000"]
