FROM python:3.12-slim
WORKDIR /app

COPY engine/requirements.txt .
COPY engine/main.py .
COPY src ./src

# Install system dependencies and Stockfish 17.1 binary for Ubuntu AVX2
RUN apt-get update && \
    apt-get install -y wget tar && \
    wget https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-ubuntu-x86-64-avx2.tar && \
    tar -xf stockfish-ubuntu-x86-64-avx2.tar && \
    ls -l stockfish && \
    mkdir -p /usr/local/bin && \
    mv stockfish/stockfish* /usr/local/bin/stockfish && \
    chmod +x /usr/local/bin/stockfish && \
    rm -rf stockfish-ubuntu-x86-64-avx2.tar stockfish

RUN pip install --no-cache-dir stockfish && \
    python -c "import stockfish; print('stockfish Python package is installed and importable')" && \
    pip install --no-cache-dir python-dotenv && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import dotenv; print('python-dotenv is installed and importable')"

ENV PYTHONPATH="${PYTHONPATH}:/app/src"

# Diagnostics: show /app dir and main.py after copy
RUN echo "Listing /app directory after COPY:" && ls -l /app && \
    echo "Showing first 20 lines of /app/main.py after COPY:" && head -20 /app/main.py

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]