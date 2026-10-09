# SGJobs Decoupled Dashboard

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
