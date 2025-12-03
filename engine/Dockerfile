FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY engine/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y wget tar && \
    pip install --no-cache-dir stockfish

# Copy the entire engine directory
COPY engine ./engine

# Copy shared user_data directory
COPY user_data ./user_data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]