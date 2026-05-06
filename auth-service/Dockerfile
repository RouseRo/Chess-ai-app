FROM python:3.12-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY auth-service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy auth service code
COPY auth-service ./auth-service

# Copy shared engine code
COPY engine ./engine

# Copy user_data directory for data persistence
COPY user_data ./user_data

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the auth service
CMD ["uvicorn", "auth-service.main:app", "--host", "0.0.0.0", "--port", "8002"]