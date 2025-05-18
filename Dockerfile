FROM python:3.11.8-slim-bookworm

# Update packages and apply security fixes
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv (fast dependency manager)
RUN pip install --no-cache-dir uv

# Copy only dependency files first for better caching
COPY pyproject.toml .
COPY setup.py .

# Install Python dependencies (cached unless these files change)
RUN uv pip install --system -e .

# Install Kafka client
RUN uv pip install --system confluent-kafka

# Now copy the rest of your code
COPY . .

# Set environment variables for Python (optional, but recommended)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default command (can be overridden in docker-compose.yml)
CMD ["python", "-m", "src.pipeline.run_pipeline", "--config", "config/default.yaml"]