#!/bin/sh
# start the model server, wait until it answers, then start the web app on Cloud Run's port
ollama serve > /tmp/ollama.log 2>&1 &
until ollama list > /dev/null 2>&1; do sleep 1; done
exec streamlit run /app/app_local.py --server.port "${PORT:-8080}" --server.address 0.0.0.0
