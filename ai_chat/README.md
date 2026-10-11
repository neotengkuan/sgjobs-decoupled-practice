# SGJobs AI Chat (voice + text)

<!-- LINKS START -->
## Live links (updated 2026-10-11)

| What | Where it runs | Link |
|---|---|---|
| Streamlit dashboard (original, reads parquet) | Streamlit Community Cloud | https://YOUR-APP.streamlit.app |
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

## Local version: open-source Hugging Face models, served through a Cloudflare tunnel

`app_local.py` answers the same questions with **no per-question AI cost**:

| Job | Model | Runs on |
|---|---|---|
| Listen (voice → text) | Whisper `base.en` (faster-whisper, from Hugging Face) | my laptop |
| Think and answer | Qwen 2.5 1.5B Instruct GGUF (from Hugging Face) via Ollama | my laptop (Docker Desktop) |
| Data | SGJobs FastAPI backend | Google Cloud Run |

Because a 1.5B model is weak at tool calling, the app works in two steps: the model plans the
endpoint and filters as JSON, Python validates every filter against `/api/filters`, then the model
summarises the API result. Python flags any number in the answer that isn't in the data.

**Public access without hosting cost:** `cloudflared tunnel --url http://localhost:8503` gives
a temporary public HTTPS link that forwards to the app on my laptop. Tested working from a phone
on 2026-10-10. Live demo available on request (the link only works while my laptop is running).

Run locally:

    conda create -n aichat python=3.11 -y && conda activate aichat
    pip install -r requirements_local.txt
    streamlit run app_local.py --server.port 8503

Local flow:

    phone / browser
       -> Cloudflare tunnel (free public HTTPS link)
       -> my laptop: Streamlit app_local.py
            -> Whisper (voice -> text, local)
            -> Qwen 2.5 in Ollama (plans endpoint + filters as JSON, local)
            -> SGJobs FastAPI backend on Cloud Run (data)
            -> Qwen writes the answer; Python flags numbers not in the data
       -> answer back through the tunnel
