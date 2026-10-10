# SGJobs Decoupled Dashboard

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
