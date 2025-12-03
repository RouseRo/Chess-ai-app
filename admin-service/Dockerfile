FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY admin-service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy admin service code
COPY admin-service ./admin-service

# Copy shared engine code
COPY engine ./engine

# Copy user_data directory for data persistence
COPY user_data ./user_data

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8001/health')"

# Run the admin service
CMD ["uvicorn", "admin-service.main:app", "--host", "0.0.0.0", "--port", "8001"]