FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY engine/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    apt-get update && \
    apt-get install -y wget tar && \
    pip install --no-cache-dir stockfish

# Copy the entire engine directory
COPY engine ./engine

# Copy src directory for imports
COPY src ./src

# Verify files are in place
RUN echo "Listing /app directory:" && ls -la /app && \
    echo "Listing /app/engine directory:" && ls -la /app/engine

# Run the application
CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]