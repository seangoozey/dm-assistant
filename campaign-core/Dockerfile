FROM python:3.13.14-alpine3.23

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt \
    && addgroup -S campaign-core \
    && adduser -S -G campaign-core campaign-core

COPY --chown=campaign-core:campaign-core src ./src

USER campaign-core

EXPOSE 8000

CMD ["python", "-m", "dm_assistant_core.bootstrap"]

