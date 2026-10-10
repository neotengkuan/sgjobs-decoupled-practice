"""SGJobs AI Chat - LOCAL version.

Same idea as app.py, but the AI is a free Hugging Face model (Qwen2.5 GGUF) running in
Ollama on Docker Desktop, and voice is transcribed locally by faster-whisper (also from
Hugging Face). Nothing is billed per question.

Small models are weak at native tool calling, so the AI works in two short steps:
  1. PLAN    - the model turns the question into JSON {"endpoint": ..., "filters": {...}}
               and Python checks every filter value against the real /api/filters list.
  2. ANSWER  - Python calls the SGJobs API, the model summarises the returned JSON,
               and Python flags any number in the answer that is not in the data.
"""
import io, os, re, json, time, hashlib, difflib

import requests
import streamlit as st

API = os.environ.get("SGJOBS_API", "https://sgjobs-api-18035811102.us-central1.run.app")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "hf.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF:Q4_K_M")
WHISPER = os.environ.get("WHISPER_MODEL", "base.en")

ENDPOINTS = {
    "overview": ("/api/overview", "headline KPIs: job counts, vacancies, median salary"),
    "salary": ("/api/salary/analysis", "salary levels and salary bands"),
    "opportunity": ("/api/opportunity/analysis", "opportunity scores and bands"),
    "demand": ("/api/demand/analysis", "demand by seniority, experience and vacancies"),
    "skills_categories": ("/api/skills-categories/analysis", "top skills and job categories"),
    "repost": ("/api/repost/analysis", "reposted job ads"),
    "data_quality": ("/api/data-quality/analysis", "outliers and records needing review"),
}
FILTER_KEYS = ["employment_types", "category_primary", "category_bridge", "skill_bridge",
               "seniority_group", "experience_band", "vacancy_band", "salary_band",
               "opportunity_band", "posting_year"]


# ---------------------------------------------------------------- backend
def api_get(path, params=None):
    params = {k: v for k, v in (params or {}).items() if v not in (None, [], "")}
    r = requests.get(API + path, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def _as_strings(values):
    out = []
    for v in values if isinstance(values, list) else []:
        if isinstance(v, dict):                     # e.g. {"value": "IT", "count": 12}
            v = v.get("value") or v.get("name") or v.get("label") or next(iter(v.values()), None)
        if v not in (None, ""):
            out.append(str(v))
    return out


@st.cache_data(ttl=3600)
def valid_filters():
    raw = api_get("/api/filters")
    if isinstance(raw, dict) and "filters" in raw and isinstance(raw["filters"], dict):
        raw = raw["filters"]
    return {k: _as_strings(raw.get(k, [])) for k in FILTER_KEYS} if isinstance(raw, dict) else {}


def match_filters(asked):
    """Keep only filter values that exist; fix near-misses (e.g. 'it' -> 'Information Technology')."""
    allowed, used, notes = valid_filters(), {}, []
    for key, vals in (asked or {}).items():
        if key not in FILTER_KEYS:
            continue
        vals = vals if isinstance(vals, list) else [vals]
        choices = allowed.get(key, [])
        lower = {c.lower(): c for c in choices}
        for v in vals:
            v = str(v).strip()
            if not v:
                continue
            hit = lower.get(v.lower())
            if not hit and choices:                  # initials, e.g. "IT" -> "Information Technology"
                hit = next((c for c in choices if len(c.split()) > 1 and
                            "".join(w[0] for w in re.findall(r"[A-Za-z]+", c)).lower() == v.lower()), None)
            if not hit and choices and len(v) > 3:
                hit = next((c for c in choices if v.lower() in c.lower()), None)
            if not hit and choices:
                close = difflib.get_close_matches(v, choices, n=1, cutoff=0.6)
                hit = close[0] if close else None
            if not choices and key == "posting_year" and v.isdigit():
                hit = v
            if hit:
                used.setdefault(key, []).append(hit)
                if hit != v:
                    notes.append(f"'{v}' → '{hit}'")
            else:
                notes.append(f"dropped '{v}' (not a valid {key})")
    return used, notes


# ---------------------------------------------------------------- local model (Ollama)
def ollama_chat(messages, json_mode=False):
    body = {"model": MODEL, "messages": messages, "stream": False, "keep_alive": "30m",
            "options": {"temperature": 0.1, "num_ctx": 8192}}
    if json_mode:
        body["format"] = "json"
    r = requests.post(f"{OLLAMA}/api/chat", json=body, timeout=600)
    r.raise_for_status()
    return r.json()["message"]["content"].strip()


def filter_menu():
    lines = []
    for k, vals in valid_filters().items():
        shown = ", ".join(vals[:25]) + (f", … ({len(vals)} total)" if len(vals) > 25 else "")
        lines.append(f"- {k}: {shown or '(any)'}")
    return "\n".join(lines)


def plan(question, history):
    system = (
        "You convert questions about Singapore job postings into an API request. "
        "Reply with JSON only, shaped exactly like "
        '{"endpoint": "salary", "filters": {"category_primary": ["Information Technology"]}}.\n'
        "Endpoints:\n" + "\n".join(f"- {k}: {d}" for k, (_, d) in ENDPOINTS.items()) +
        "\nFilters (use only if the question asks for them; values must come from these lists):\n" +
        filter_menu())
    recent = "\n".join(f"{m['role']}: {m['content']}" for m in history[-4:])
    raw = ollama_chat([{"role": "system", "content": system},
                       {"role": "user", "content": f"Earlier conversation:\n{recent}\n\nQuestion: {question}"}],
                      json_mode=True)
    try:
        p = json.loads(raw)
    except json.JSONDecodeError:
        p = {}
    endpoint = p.get("endpoint") if p.get("endpoint") in ENDPOINTS else "overview"
    filters, notes = match_filters(p.get("filters") or {})
    return endpoint, filters, notes, raw


def answer(question, endpoint, filters, data):
    text = json.dumps(data, default=str)[:6000]
    system = ("You are a job-market analyst. Answer ONLY from the JSON data given. "
              "Copy numbers exactly as they appear - do not round, shorten or invent them. "
              "Salaries are in SGD. Never claim to have done anything other than read this data. "
              "Answer in 2-4 short sentences and mention the filters used.")
    user = f"Question: {question}\nEndpoint: {endpoint}\nFilters: {filters or 'none'}\nDATA:\n{text}"
    return ollama_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])


# ---------------------------------------------------------------- number check (catches garbled figures)
def _numbers(s):
    return [n.replace(",", "") for n in re.findall(r"\d[\d,]*\.?\d*", s)]


def unverified_numbers(reply, data):
    known = set()
    for n in _numbers(json.dumps(data, default=str)):
        try:
            x = float(n)
        except ValueError:
            continue
        for y in (x, x * 100):
            known.update({f"{y:.0f}", f"{y:.1f}", f"{y:.2f}", n})
    bad = []
    for n in _numbers(reply):
        n = n.rstrip(".")
        if len(n.replace(".", "")) < 3:          # ignore small numbers like 2 or 25
            continue
        try:
            x = float(n)
        except ValueError:
            continue
        if not ({n, f"{x:.0f}", f"{x:.1f}", f"{x:.2f}"} & known):
            bad.append(n)
    return bad


# ---------------------------------------------------------------- voice (local Whisper + gTTS)
@st.cache_resource
def whisper():
    from faster_whisper import WhisperModel          # Hugging Face Systran/faster-whisper-*
    return WhisperModel(WHISPER, device="cpu", compute_type="int8")


def transcribe(audio_bytes):
    segments, _ = whisper().transcribe(io.BytesIO(audio_bytes), language="en")
    return " ".join(s.text for s in segments).strip()


def speak(text):
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=text.replace("*", ""), lang="en").write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- page
st.set_page_config(page_title="SGJobs AI Chat (local)", page_icon="🖥️")
st.title("🖥️ SGJobs AI Chat — local Hugging Face model")
st.caption(f"Model: {MODEL} via Ollama on Docker Desktop · no per-question cost · slower than the cloud version")

with st.sidebar:
    voice_reply = st.toggle("🔊 Read answers aloud (gTTS, needs internet)", value=False)
    show_plan = st.toggle("Show the model's raw plan", value=False)
    st.markdown("**Try:**\n- Median salary for IT jobs?\n- Top skills for senior roles?"
                "\n- How many jobs were reposted in 2023?")

st.session_state.setdefault("history", [])
st.session_state.setdefault("last_audio", None)


def show_extras(m):
    st.caption(f"🔧 {m['path']}  {m['filters'] or '(no filters)'}  ·  ⏱ {m['secs']:.0f}s")
    for n in m["notes"]:
        st.caption(f"↪ {n}")
    if m["bad"]:
        st.warning("These numbers are not in the data, so the model may have garbled them: "
                   + ", ".join(m["bad"]) + ". Check the data below.")
    with st.expander("📄 Data returned by the API"):
        st.json(m["data"])
    if show_plan:
        st.code(m["raw_plan"], language="json")


for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"].replace("$", r"\$"))
        if m["role"] == "assistant" and "path" in m:
            show_extras(m)

question = None
audio = st.audio_input("🎙️ Ask by voice (transcribed on your computer)")
if audio is not None:
    audio_bytes = audio.getvalue()
    digest = hashlib.md5(audio_bytes).hexdigest()
    if digest != st.session_state.last_audio:
        st.session_state.last_audio = digest
        with st.spinner("Transcribing locally with Whisper…"):
            try:
                question = transcribe(audio_bytes)
            except Exception as e:
                st.error(f"Voice needs faster-whisper installed: {e}")

typed = st.chat_input("…or type your question")
if typed:
    question = typed

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        t0 = time.time()
        try:
            with st.spinner("Step 1/2: the local model is choosing the endpoint and filters…"):
                endpoint, filters, notes, raw_plan = plan(question, st.session_state.history[:-1])
            path = ENDPOINTS[endpoint][0]
            with st.spinner(f"Calling {path}…"):
                data = api_get(path, filters)
            with st.spinner("Step 2/2: the local model is writing the answer…"):
                reply = answer(question, endpoint, filters, data)
        except requests.ConnectionError:
            st.error(f"Can't reach Ollama at {OLLAMA} or the API at {API}. Is the Ollama container running?")
            st.stop()
        msg = {"role": "assistant", "content": reply, "path": path, "filters": filters, "notes": notes,
               "data": data, "raw_plan": raw_plan, "bad": unverified_numbers(reply, data),
               "secs": time.time() - t0}
        st.markdown(reply.replace("$", r"\$"))
        show_extras(msg)
        if voice_reply:
            st.audio(speak(reply), format="audio/mp3", autoplay=True)
    st.session_state.history.append(msg)
