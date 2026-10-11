# Qwen (Ollama) + Whisper + Streamlit in one container, for Cloud Run
FROM ollama/ollama:latest
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY requirements_local.txt .
RUN pip install --no-cache-dir -r requirements_local.txt
# bake both models into the image so a cold start doesn't download them
ENV OLLAMA_MODEL=hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M
RUN (ollama serve > /tmp/ollama.log 2>&1 &) \
    && until ollama list > /dev/null 2>&1; do sleep 1; done \
    && ollama pull "$OLLAMA_MODEL"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', device='cpu', compute_type='int8')"
COPY app_local.py start.sh ./
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh
ENV OLLAMA_URL=http://localhost:11434
ENTRYPOINT ["/app/start.sh"]
