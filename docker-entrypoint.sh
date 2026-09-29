#!/bin/sh
set -e

# Pastikan folder volume ada
mkdir -p /app/data /app/faiss_index /app/knowledge_base /home/appuser/.cache/huggingface

# Jika volume /app/faiss_index kosong (misal karena bind mount host baru yang belum ada filenya),
# pulihkan dari cadangan image agar startup instan tanpa perlu komputasi ulang
if [ ! -f "/app/faiss_index/index.faiss" ] && [ -d "/app/faiss_index_default" ]; then
    echo "[INFO] faiss_index kosong di volume host, memulihkan file index dari image..."
    cp -r /app/faiss_index_default/* /app/faiss_index/ 2>/dev/null || true
fi

# Pastikan seluruh hak kepemilikan folder volume dipegang oleh appuser (UID 1000)
chown -R appuser:appuser /app/data /app/faiss_index /app/knowledge_base /home/appuser

# Jalankan perintah container sebagai appuser
exec gosu appuser "$@"
