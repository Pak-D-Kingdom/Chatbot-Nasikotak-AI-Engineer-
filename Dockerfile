# Gunakan image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app
ENV PYTHONPATH=/app

# Install dependensi sistem yang mungkin dibutuhkan oleh library (misal faiss)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt dan install dependensi Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy seluruh source code ke dalam container
COPY . .

# Buat user non-root untuk keamanan, siapkan direktori, dan ubah kepemilikan
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /app/faiss_index /app/knowledge_base /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser

# Pindah ke user non-root
USER appuser

# Expose port 8001 untuk FastAPI
EXPOSE 8001

# Perintah untuk menjalankan aplikasi
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
