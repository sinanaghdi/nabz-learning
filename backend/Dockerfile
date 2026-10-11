FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

# This image is the local development image. Production deployments should run
# migrations as a separate release step rather than on every application start.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
