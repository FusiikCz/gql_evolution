# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3.10.13-slim AS prepare

# instalace curl a git, aby bylo mozne zprovoznit standardni healthcheck a instalovat z git
RUN apt update && apt install curl git -y && rm -rf /var/cache/apk/*

EXPOSE 8000

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Install pip requirements
COPY azure_proxy/requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY azure_proxy/ /app/
COPY src/ /app/src/

RUN useradd appuser && chown -R appuser /app
USER appuser

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
#CMD ["gunicorn", "--reload=True", "--bind", "0.0.0.0:8000", "-k", "uvicorn.workers.UvicornWorker", "app:app"]
#CMD ["gunicorn", "--bind", "0.0.0.0:8000", "-t", "300", "-k", "uvicorn.workers.UvicornWorker", "main:app"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
