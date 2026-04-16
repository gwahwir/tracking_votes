FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: override in docker-compose per service
CMD ["uvicorn", "control_plane.server:app", "--host", "0.0.0.0", "--port", "8000"]
