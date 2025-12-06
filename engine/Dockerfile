FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Stockfish
RUN apt-get update && apt-get install -y \
    curl \
    stockfish \
    && rm -rf /var/lib/apt/lists/*

# Verify Stockfish installation and find its path
RUN which stockfish && stockfish --help || echo "Stockfish installed"

# Copy requirements and install
COPY engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY engine/ ./engine/
COPY src/ ./src/
COPY user_data/ ./user_data/

# Set Stockfish path environment variable (Debian/Ubuntu path)
ENV STOCKFISH_PATH=/usr/games/stockfish

EXPOSE 8000

CMD ["uvicorn", "engine.main:app", "--host", "0.0.0.0", "--port", "8000"]