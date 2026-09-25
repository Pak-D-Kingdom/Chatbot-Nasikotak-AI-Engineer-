#!/bin/sh
set -e

# Pastikan folder volume ada dan dimiliki oleh appuser (UID 1000)
mkdir -p /app/data /app/faiss_index /app/knowledge_base /home/appuser/.cache/huggingface
chown -R appuser:appuser /app/data /app/faiss_index /app/knowledge_base /home/appuser

# Jalankan perintah container sebagai appuser
exec gosu appuser "$@"
