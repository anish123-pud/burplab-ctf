FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --yes --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system burplab \
    && adduser --system --ingroup burplab burplab

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=burplab:burplab . .
RUN chmod 755 /app/docker-entrypoint.sh

USER burplab

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "run.py"]
