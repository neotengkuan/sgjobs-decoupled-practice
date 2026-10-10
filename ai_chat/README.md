# SGJobs AI Chat (voice + text)

**Live demo:** https://sgjobs-ai-chat-jimvxb6tlq-uc.a.run.app
Deployed to Google Cloud Run on 2026-10-10.

Ask questions about ~1 million Singapore job postings by voice or text. No filters or slicers needed:
the AI (Gemini on Vertex AI) decides which SGJobs API endpoint to call and which filters to apply,
then answers in plain English and reads the answer aloud.

## How it works
```
voice / text question
   -> Gemini (transcribes voice, chooses an endpoint + filters via tool calling)
   -> SGJobs FastAPI backend (15 endpoints, also used by the Streamlit and React dashboards)
   -> JSON result -> Gemini writes the answer -> gTTS reads it aloud
```
Each answer shows the endpoint and filters the AI called, so every number can be checked.

## Related services
- FastAPI backend: https://sgjobs-api-18035811102.us-central1.run.app/docs
- Streamlit dashboard: https://sgjobs-streamlit-18035811102.us-central1.run.app
- React dashboard: https://sgjobs-react-18035811102.us-central1.run.app

## Example questions
- What is the median salary for IT jobs?
- Which skills are most in demand for senior roles?
- How many jobs were reposted in 2023?
