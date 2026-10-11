# SGJobs Decoupled Dashboard

<!-- LINKS START -->
## Live links (updated 2026-10-11)

| What | Where it runs | Link |
|---|---|---|
| Streamlit dashboard (original, reads parquet) | Streamlit Community Cloud | https://sgjobs-app-dashboard-2zycahedjxbcetyeda3ut4.streamlit.app/ |
| FastAPI backend (15 endpoints) | Google Cloud Run | https://sgjobs-api-18035811102.us-central1.run.app/docs |
| Streamlit front end (calls the API) | Google Cloud Run | https://sgjobs-streamlit-18035811102.us-central1.run.app |
| React / JavaScript front end (calls the API) | Google Cloud Run | https://sgjobs-react-18035811102.us-central1.run.app |
| AI chat 1: Gemini analyst (voice + text) | Google Cloud Run + Vertex AI | https://sgjobs-ai-chat-18035811102.us-central1.run.app |
| AI chat 2: Qwen (Hugging Face) in one Docker container | Google Cloud Run | https://sgjobs-ai-hf-18035811102.us-central1.run.app |
| AI chat 3: Qwen (Hugging Face) on a laptop | Laptop + Cloudflare quick tunnel | https://pig-investigated-performing-seminar.trycloudflare.com (changes on every restart; only up while the laptop runs it) |

All three AI chats and both API front ends read the **same FastAPI backend**, so the same filters give the same figures.

| AI chat | Model | Speed | Cost |
|---|---|---|---|
| Gemini (Cloud Run) | Gemini 2.5 Flash, tool calling, several API calls per question | 3-5 s | cents per day of use |
| Qwen Docker (Cloud Run) | Qwen2.5-1.5B + faster-whisper baked into the image | 30-90 s, 1-2 min cold start | ~US$0.40/hour while a tab is open |
| Qwen laptop (tunnel) | same model via Ollama in Docker Desktop | 30-90 s | electricity only |
<!-- LINKS END -->


## Live demos
- 🎙️ AI voice/text chat: https://sgjobs-ai-chat-jimvxb6tlq-uc.a.run.app  (details: [ai_chat/](ai_chat/))
- React dashboard: https://sgjobs-react-18035811102.us-central1.run.app
- Streamlit dashboard: https://sgjobs-streamlit-18035811102.us-central1.run.app
- FastAPI backend docs: https://sgjobs-api-18035811102.us-central1.run.app/docs





This project documents the migration of the SGJobs analytics dashboard from a Streamlit application into a decoupled architecture with a reusable FastAPI backend and two independently deployed frontends.

## Current Architecture

```text
                         ┌─────────────────────────────┐
                         │           Browser           │
                         └──────────────┬──────────────┘
                                        │
                          ┌─────────────┴─────────────┐
                          │                           │
                          ▼                           ▼
             ┌──────────────────────┐     ┌──────────────────────┐
             │   sgjobs-react       │     │  sgjobs-streamlit    │
             │ React + Vite + Nginx │     │ Streamlit frontend   │
             │ Cloud Run            │     │ Cloud Run            │
             └──────────┬───────────┘     └──────────┬───────────┘
                        │ /api/*                     │ HTTP API
                        └──────────────┬──────────────┘
                                       ▼
                           ┌──────────────────────┐
                           │     sgjobs-api       │
                           │ FastAPI + Uvicorn    │
                           │ Cloud Run            │
                           └──────────┬───────────┘
                                      │
                       ┌──────────────┼──────────────┐
                       ▼              ▼              ▼
                  Main Parquet   Category Bridge   Skill Bridge
