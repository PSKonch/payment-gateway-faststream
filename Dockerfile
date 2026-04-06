FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md alembic.ini /app/
COPY app /app/app
COPY provider /app/provider
COPY scripts /app/scripts
COPY migrations /app/migrations

RUN pip install --no-cache-dir --upgrade pip \
	&& pip install --no-cache-dir . \
	&& chmod +x /app/scripts/entrypoint.sh

EXPOSE 8000

CMD ["/app/scripts/entrypoint.sh"]