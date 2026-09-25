# Gunakan image Python yang ringan
FROM python:3.11-slim

# Set working directory di dalam container
WORKDIR /app
ENV PYTHONPATH=/app

# Install dependensi sistem yang mungkin dibutuhkan oleh library (misal faiss) dan gosu
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt dan install dependensi Python
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy seluruh source code ke dalam container
COPY . .

# Buat salinan cadangan faiss_index agar bisa dipulihkan saat volume host kosong
RUN cp -r /app/faiss_index /app/faiss_index_default

# Buat user non-root untuk keamanan, siapkan direktori, dan ubah kepemilikan
RUN useradd -m -u 1000 appuser \
    && mkdir -p /app/data /app/faiss_index /app/knowledge_base /home/appuser/.cache/huggingface \
    && chown -R appuser:appuser /app /home/appuser

# Setup entrypoint script untuk menangani permission volume secara otomatis
COPY docker-entrypoint.sh /usr/local/bin/
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose port 8001 untuk FastAPI
EXPOSE 8001

ENTRYPOINT ["docker-entrypoint.sh"]

# Perintah untuk menjalankan aplikasi
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
