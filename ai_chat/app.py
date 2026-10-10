"""SGJobs AI Chat - voice/text questions answered by Gemini, which calls the SGJobs FastAPI backend as tools."""
import io, os, json, hashlib
from typing import List, Optional

import requests
import streamlit as st
from google import genai
from google.genai import types
from gtts import gTTS

API = os.environ.get("SGJOBS_API", "https://sgjobs-api-18035811102.us-central1.run.app")
PROJECT = os.environ.get("GCP_PROJECT", "friendly-autumn-509313-n3")
LOCATION = os.environ.get("GEMINI_LOCATION", "us-central1")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

ENDPOINTS = {                      # short name the AI uses -> real backend path
    "overview": "/api/overview",
    "salary": "/api/salary/analysis",
    "opportunity": "/api/opportunity/analysis",
    "demand": "/api/demand/analysis",
    "skills_categories": "/api/skills-categories/analysis",
    "repost": "/api/repost/analysis",
    "data_quality": "/api/data-quality/analysis",
}
CALLS = []                         # log of tool calls for the current question (shown in the UI)


def _get(path, params=None):
    params = {k: v for k, v in (params or {}).items() if v not in (None, [], "")}
    r = requests.get(API + path, params=params, timeout=120)
    r.raise_for_status()
    text = json.dumps(r.json(), default=str)
    CALLS.append({"path": path, "filters": params})
    return text[:15000]            # keep the reply small enough for the model


# ---------------------------------------------------------------- tools the AI can call
def query_sgjobs(endpoint: str,
                 employment_types: Optional[List[str]] = None,
                 category_primary: Optional[List[str]] = None,
                 category_bridge: Optional[List[str]] = None,
                 skill_bridge: Optional[List[str]] = None,
                 seniority_group: Optional[List[str]] = None,
                 experience_band: Optional[List[str]] = None,
                 vacancy_band: Optional[List[str]] = None,
                 salary_band: Optional[List[str]] = None,
                 opportunity_band: Optional[List[str]] = None,
                 posting_year: Optional[List[str]] = None) -> str:
    """Query the SGJobs job-postings backend with optional filters and return its JSON result.

    Args:
        endpoint: which analysis to run. One of: overview (headline KPIs), salary (salary analysis),
            opportunity (opportunity scores), demand (demand and seniority), skills_categories
            (skills and job categories), repost (reposted jobs), data_quality (outliers and review cases).
        employment_types: e.g. ["Permanent"]. Use exact values from the valid filter list.
        category_primary: the job's main category, exact values only.
        category_bridge: any category a job belongs to (a job can have several), exact values only.
        skill_bridge: required skills, exact values only.
        seniority_group: exact values only.
        experience_band: exact values only.
        vacancy_band: exact values only.
        salary_band: exact values only.
        opportunity_band: exact values only.
        posting_year: e.g. ["2023"].
    """
    path = ENDPOINTS.get(endpoint)
    if not path:
        return json.dumps({"error": f"unknown endpoint {endpoint}; use one of {list(ENDPOINTS)}"})
    return _get(path, dict(employment_types=employment_types, category_primary=category_primary,
                           category_bridge=category_bridge, skill_bridge=skill_bridge,
                           seniority_group=seniority_group, experience_band=experience_band,
                           vacancy_band=vacancy_band, salary_band=salary_band,
                           opportunity_band=opportunity_band, posting_year=posting_year))


def get_job_details(job_post_id: str) -> str:
    """Return one job posting's full record, its categories and its skills.

    Args:
        job_post_id: the job id, e.g. "MCF-2023-0273977".
    """
    return json.dumps({"job": _get(f"/api/jobs/{job_post_id}"),
                       "categories": _get(f"/api/jobs/{job_post_id}/categories"),
                       "skills": _get(f"/api/jobs/{job_post_id}/skills")})


# ---------------------------------------------------------------- model, filters, voice
@st.cache_resource
def llm():
    return genai.Client(vertexai=True, project=PROJECT, location=LOCATION)


@st.cache_data(ttl=3600)
def valid_filters():
    r = requests.get(API + "/api/filters", timeout=120)
    return json.dumps(r.json(), default=str)[:12000]


def transcribe(audio_bytes, mime):
    r = llm().models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                  "Transcribe this audio exactly. Return only the transcript."])
    return (r.text or "").strip()


def ask_ai(history):
    system = (
        "You are a job-market analyst for SGJobs, a dataset of ~1 million Singapore job postings. "
        "ALWAYS answer by calling the query_sgjobs tool (or get_job_details) - never from memory. "
        "Turn the user's question into the right endpoint and filters. Use ONLY exact filter values "
        "from the list below; if a value doesn't match, pick the closest valid one and say which you used. "
        "Quote numbers exactly as returned; do not invent figures. Answer in 2-5 short sentences and "
        "mention the filters applied. Salaries are in SGD.\n\nVALID FILTER VALUES: " + valid_filters())
    contents = [types.Content(role="user" if m["role"] == "user" else "model",
                              parts=[types.Part(text=m["content"])]) for m in history[-8:]]
    r = llm().models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.1,
                                           tools=[query_sgjobs, get_job_details]))
    return (r.text or "Sorry, I couldn't produce an answer.").strip()


def speak(text):
    buf = io.BytesIO()
    gTTS(text=text.replace("*", ""), lang="en").write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- page
st.set_page_config(page_title="SGJobs AI Chat", page_icon="🎙️")
st.title("🎙️ SGJobs AI Chat")
st.caption("Ask by voice or text. The AI picks the right SGJobs API endpoint and filters for you - no slicers.")

with st.sidebar:
    voice_reply = st.toggle("🔊 Read answers aloud", value=True)
    st.markdown("**Try:**\n- Median salary for IT jobs?\n- Which skills are most in demand for senior roles?"
                "\n- How many jobs were reposted in 2023?\n- Compare salaries for permanent vs contract jobs")

st.session_state.setdefault("history", [])
st.session_state.setdefault("last_audio", None)

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        for c in m.get("calls", []):
            st.caption(f"🔧 {c['path']}  {c['filters'] or '(no filters)'}")

question = None
audio = st.audio_input("🎙️ Ask by voice")
if audio is not None:
    audio_bytes = audio.getvalue()
    digest = hashlib.md5(audio_bytes).hexdigest()
    if digest != st.session_state.last_audio:          # handle each recording once
        st.session_state.last_audio = digest
        with st.spinner("Transcribing…"):
            question = transcribe(audio_bytes, audio.type or "audio/wav")

typed = st.chat_input("…or type your question")
if typed:
    question = typed

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        CALLS.clear()
        with st.spinner("Querying the SGJobs backend…"):
            answer = ask_ai(st.session_state.history)
        st.markdown(answer)
        calls = list(CALLS)
        for c in calls:
            st.caption(f"🔧 {c['path']}  {c['filters'] or '(no filters)'}")
        if voice_reply:
            st.audio(speak(answer), format="audio/mp3", autoplay=True)
    st.session_state.history.append({"role": "assistant", "content": answer, "calls": calls})
