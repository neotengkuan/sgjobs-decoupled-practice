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


GLOSSARY = (
    "DEFINITIONS (use these, not general knowledge; definition questions are answered from here): "
    "opportunity_score = (0.40 x (1 - competition_rank_pct) + 0.30 x vacancy_rank_pct + 0.30 x salary_rank_pct) x 100, "
    "where each is a 0-1 percentile rank of applications_per_vacancy, number_of_vacancies and salary_midpoint; "
    "low competition, many vacancies and high pay give a high score. Weights are analyst choices, not machine learning. "
    "opportunity_band: Low (<=40), Moderate (40-60), Good (60-80), High (>80). There is no Medium band; medium means "
    "Moderate. It is NOT based on salary alone and is an exploratory index, not a prediction. "
    "salary_midpoint = (min + max) / 2, the centre of the advertised range, not the pay received. "
    "applications_per_vacancy = applications / vacancies; application_rate = applications / views. "
    "A job can have 1-5 Job Functions: category_bridge keeps all of them (one row per job-function pair, counted by "
    "distinct job), category_primary is only the first one listed. skill tags come from keywords in the job title. "
    "is_reposted = repost count > 0; repost rate shows behaviour, not the employer's reason. "
    "The V3 table has 71 columns: 22 raw plus 49 cleaned, engineered, band, date, rank and review-flag columns. "
    "salary_band is about pay only.")

BANDS = {"high": "High", "good": "Good", "moderate": "Moderate", "medium": "Moderate",
         "average": "Moderate", "low": "Low"}


def apply_rules(question, filters, notes):
    """Deterministic rules: business terms are mapped by Python, not left to the small model."""
    q = question.lower()
    m = re.search(r"\b(" + "|".join(BANDS) + r")[\s-]+opportunit", q)
    if m:
        wanted, _ = match_filters({"opportunity_band": [BANDS[m.group(1)]]})
        if wanted.get("opportunity_band"):
            filters["opportunity_band"] = wanted["opportunity_band"]
            notes.append(f"rule: '{m.group(0)}...' -> opportunity_band = {wanted['opportunity_band'][0]}")
        if "salary_band" in filters and not re.search(r"salary band|pay band|pay level", q):
            filters.pop("salary_band")
            notes.append("rule: removed salary_band (opportunity is not judged by salary)")
    return filters, notes


# ---------------------------------------------------------------- project knowledge
# Project knowledge for the local chatbot, split into topics so the small model only reads what the question needs.
# Source: Team 6 "Feature Engineering, DAX and Python" guide and the Streamlit presentation narrative.
TOPICS = {
    "build": ("built build pipeline columns raw cleaned clean 71 22 49 v3 python power bi dataset source made created",
        "How the data was built: raw SGJobData from MyCareersFuture had 22 columns. Team 6 cleaned and "
        "feature-engineered it in Python into the validated V3 table of 1,044,597 rows and 71 columns, plus two bridge "
        "tables. The 49 added columns are not all business features: they are cleaned fields, engineered features, "
        "bands, date helpers, percentile ranks, data-quality and review flags, and a pipeline row id. The dashboard was "
        "built first in Power BI, then in Streamlit with 18 DAX-equivalent measures; this practice version has a FastAPI "
        "backend with Streamlit and React front ends on Google Cloud Run, and this chatbot calls the same API."),
    "columns": ("49 columns column extra added families fields features",
        "The 49 added columns by family: salary (salary_midpoint, salary_range, salary_range_pct, salary_band, "
        "salary_type_clean); experience_band; vacancy_band; seniority (position_level_clean, seniority_group); demand and "
        "competition (applications_per_vacancy, views_per_vacancy, application_rate); Job Function (category_primary, "
        "category_primary_id, category_count); skills (title_clean, skill_tags, skill_count); time and repost (posting "
        "year, quarter, month, week, day, day of week, month_year, posting_duration_days, is_reposted); quality "
        "(salary validity flags, duplicate_job_id, has_data_quality_issue, job_id_format and review flags); opportunity "
        "(competition_rank_pct, vacancy_rank_pct, salary_rank_pct, opportunity_score, opportunity_band)."),
    "pages": ("pages page dashboard analyses analysis can you do what sections overview",
        "The dashboard has 8 pages: 1 Overview (market size, employment types, top Job Functions, trends); 2 Salary "
        "Analysis (salary as a distribution, mean vs median); 3 Opportunity Analysis (the Opportunity Score and what "
        "drives it); 4 Demand and Seniority (vacancies vs applicant competition); 5 Skills and Categories (Job Functions "
        "via the bridge, title-keyword skills); 6 Data Quality and Outliers (review flags); 7 Repost Analysis; 8 Detail "
        "Drillthrough (one job's source and derived fields). Filters: employment type, Job Function, skill, seniority, "
        "experience, vacancy band, salary band, opportunity band and year."),
    "bridge": ("bridge bridges category categories function functions primary many skill skills why",
        "Why bridges: one posting can have 1 to 5 employer-selected Job Functions (43 in total). The category bridge "
        "keeps one row per job-function pair (1,767,829 rows) so secondary functions are not lost; a job id repeating "
        "there is not a duplicate posting. category_primary is only the first function listed, a convenience field, not "
        "proof of the employer's main function. The skill bridge does the same for skill tags found by keywords in the "
        "job title (Python, SQL, Cloud, AWS, Sales and so on). Bridge counts use distinct job ids so no job is "
        "double-counted."),
    "opportunity": ("opportunity score band calculated calculation formula weight weights high good moderate low rank",
        "Opportunity Score = (0.40 x (1 - competition_rank_pct) + 0.30 x vacancy_rank_pct + 0.30 x salary_rank_pct) x "
        "100. Each input is a 0 to 1 percentile rank of applications per vacancy, number of vacancies and salary "
        "midpoint, because they are on different scales. Lower competition, more vacancies and higher pay raise the "
        "score. Example: ranks 0.20, 0.80, 0.70 give 0.32 + 0.24 + 0.21 = 77. Bands: Low up to 40, Moderate 40 to 60, "
        "Good 60 to 80, High above 80. The 40/30/30 weights are analyst choices, not machine learning; it is an "
        "exploratory screening index, not a prediction or career advice."),
    "measures": ("18 measures measure dax kpi kpis power bi",
        "The 18 measures: Total Job Postings, Unique Job Postings, Total Applications, Total Vacancies, Average Salary "
        "Midpoint, Median Salary Midpoint, Average Application Rate, Average Applications per Vacancy, Average Views per "
        "Vacancy, Average Minimum Experience, Overall Applications per Vacancy, High Opportunity Jobs, Data Quality Issue "
        "Rate, Repost Rate, Distinct Categories, Distinct Skills, Category Job Postings and Skill Job Postings. Measures "
        "recalculate for the current filters; columns are fixed per row."),
    "competition": ("applications vacancy vacancies competition demand views rate ratio average overall per",
        "applications_per_vacancy = applications / vacancies (competition per opening); views_per_vacancy = views / "
        "vacancies; application_rate = applications / views. Average applications per vacancy is the mean of each job's "
        "ratio; overall applications per vacancy is total applications / total vacancies, which weights big hiring "
        "postings more. They answer different questions. These are platform activity, not proof of attractiveness."),
    "salary": ("salary pay midpoint median mean average band paid wage",
        "salary_midpoint = (minimum + maximum) / 2, the centre of the advertised range, not the pay received. Salary "
        "bands: under 3K, 3K-5K, 5K-7K, 7K-10K, 10K+. Compare mean with median: a large gap suggests outliers or skew; "
        "check seniority mix and data-quality flags before concluding a group is genuinely high-paying."),
    "quality": ("quality flag flags review outlier outliers invalid duplicate deleted issue",
        "Data quality: has_data_quality_issue is true if salary minimum or maximum is 0 or less, maximum is below "
        "minimum, or the job id is duplicated. Review flags (salary_high, experience_high, vacancy_high, vacancy_999, "
        "needs_source_review) mark unusual values that are kept. The rule is preserve, flag, disclose, verify with the "
        "data owner; structural checks do not catch every implausible value."),
    "repost": ("repost reposted reposting rate duration expiry",
        "is_reposted = repost count above 0; posting_duration_days = expiry date minus posting date. A repost rate shows "
        "behaviour, not motive: it may be consistent with recruitment difficulty, but could also be batch hiring or "
        "routine posting, so never say employers reposted because they could not find candidates."),
    "seniority": ("seniority senior junior manager entry executive experience level band years",
        "seniority_group simplifies position levels into Entry Level, Junior, Non-Executive, Senior, Manager, "
        "Professional, Executive and Other. experience_band: No experience required, 1-2, 3-5, 6-10, 10+ years. "
        "vacancy_band: 1, 2-3, 4-10, 10+ vacancies."),
    "method": ("really truly genuinely why investigate conclusion workflow compare trust",
        "Investigation method: define the population, measure, compare, investigate, validate, then give a qualified "
        "conclusion. To test if a Job Function is truly high opportunity, check its size, what drives the score, "
        "vacancies and competition, mean vs median salary, and data-quality flags. Use 'shows' or 'suggests', not "
        "'proves' or 'caused by'."),
}


def topic_scores(question):
    words = set(re.findall(r"[a-z0-9]+", question.lower()))
    words |= {w[:-1] for w in words if w.endswith("s")}
    return sorted(((len(words & set(kw.split())), name) for name, (kw, _) in TOPICS.items()), reverse=True)


def relevant_knowledge(question, k=2):
    """Pick the k topics whose keywords best match the question (simple keyword retrieval)."""
    return "\n".join(TOPICS[name][1] for score, name in topic_scores(question)[:k] if score > 0)


DATA_CUES = (r"how many|number of|\bmedian\b|mean salary|average salary|\bcount\b|\btop \d|\bmost\b|highest|lowest|"
             r"compare|trend|\b202[34]\b|really|truly|genuinely|salary for|jobs in|\bit jobs\b|percentage|share of|"
             r"which (job|function|skill|categor|seniority)")
META = (r"how (did|do|does|was|were|is|are) (you|they|the|this|it|team)?.*(build|built|create|made|calculat|derive|work|do it)|"
        r"explain|what (is|are|does) (the |a |an )?(\d+ )?(measure|column|bridge|opportunity score|band|page|analys|flag)|"
        r"\bwhy\b.*(bridge|column|measure)|what does .* mean\b|\bdefin|\bmeaning\b|\bformula\b|what can you do")


def is_concept_question(question):
    """True for questions about how the project/data was built or what a term means (answered from the docs,
    no API call). Questions asking for figures stay data questions."""
    q = question.lower()
    best = topic_scores(q)[0][0]
    if re.search(DATA_CUES, q):
        return False
    return bool(re.search(META, q)) or best >= 2


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
    if isinstance(raw, dict) and "filters" in raw:
        raw = raw["filters"]
    if isinstance(raw, list):                          # API shape: [{"param": ..., "options": [...]}, ...]
        raw = {f["param"]: f.get("options", []) for f in raw if isinstance(f, dict) and "param" in f}
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
        + GLOSSARY + "\n"
        "Endpoints:\n" + "\n".join(f"- {k}: {d}" for k, (_, d) in ENDPOINTS.items()) +
        "\nFilters (use only if the question asks for them; values must come from these lists):\n" +
        filter_menu())
    recent = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in history[-4:])
    prev = next((m.get("filters") for m in reversed(history) if m.get("role") == "assistant" and "filters" in m), None)
    follow = (f"\nPrevious filters: {json.dumps(prev)}. If this question is a follow-up (e.g. 'same for Senior', "
              "'what about 2024', 'only permanent', 'why'), start from the previous filters and change only what "
              "the question asks." if prev else "")
    raw = ollama_chat([{"role": "system", "content": system},
                       {"role": "user", "content": f"Earlier conversation:\n{recent}{follow}\n\nQuestion: {question}"}],
                      json_mode=True)
    try:
        p = json.loads(raw)
    except json.JSONDecodeError:
        p = {}
    endpoint = p.get("endpoint") if p.get("endpoint") in ENDPOINTS else "overview"
    filters, notes = match_filters(p.get("filters") or {})
    filters, notes = apply_rules(question, filters, notes)
    if ("opportunity_band" in filters and endpoint in ("salary", "overview")
            and not re.search(r"salary|pay|wage|income", question.lower())):
        notes.append(f"rule: endpoint {endpoint} -> opportunity")
        endpoint = "opportunity"
    return endpoint, filters, notes, raw


def answer(question, endpoint, filters, data):
    text = json.dumps(data, default=str)
    if len(text) > 8000:                       # fits Qwen's 8k-token window; flag the cut
        text = text[:8000] + " ... [TRUNCATED: say that part of the data was not read]"
    background = relevant_knowledge(question)
    system = ("You are an SGJobs labour-market analyst explaining results to a business audience. Use ONLY the JSON "
              "data and the BACKGROUND and DEFINITIONS given. " + GLOSSARY + " "
              "Copy numbers exactly as they appear in the data - never invent figures. Salaries are in SGD. "
              "Answer the question asked directly. Write 4 to 7 sentences in plain prose (no bullet points), using these as a guide where the data allows: "
              "1) say which population the figures describe (the filters); "
              "2) give the key figures that answer the question; "
              "3) add context or a comparison from the data, e.g. mean versus median, or this group versus others; "
              "4) point out one thing worth noticing, such as a big mean-median gap or a small number of jobs; "
              "5) end with one suggested next question the user could ask, as a natural sentence. "
              "Only mention figures that are in the DATA and relate to the question; do not describe unrelated metrics. "
              "Say 'shows' or 'suggests', never 'proves'.")
    user = (f"Question: {question}\nEndpoint: {endpoint}\nFilters: {filters or 'none'}\n"
            f"BACKGROUND:\n{background or '(none needed)'}\nDATA:\n{text}")
    return ollama_chat([{"role": "system", "content": system}, {"role": "user", "content": user}])


def answer_concept(question):
    background = relevant_knowledge(question, k=3)
    system = ("You explain Team 6's SGJobs project to a business audience. Answer ONLY from the BACKGROUND text - "
              "do not add facts, numbers or names that are not in it. Write 4 to 7 sentences of plain prose (no bullet "
              "points), answering exactly what was asked, and end with one suggested next question the user could ask.")
    user = f"Question: {question}\nBACKGROUND:\n{background}"
    return ollama_chat([{"role": "system", "content": system}, {"role": "user", "content": user}]), background


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


def wav_to_array(audio_bytes):
    """Browser recordings from st.audio_input are WAV: decode with Python's wave module and
    resample to the 16 kHz mono float array Whisper expects (no PyAV needed)."""
    import wave
    import numpy as np
    with wave.open(io.BytesIO(audio_bytes)) as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    a = np.frombuffer(raw, dtype={1: np.uint8, 2: np.int16, 4: np.int32}[width]).astype(np.float32)
    a = (a - 128) / 128 if width == 1 else a / float(2 ** (8 * width - 1))
    if channels > 1:
        a = a.reshape(-1, channels).mean(axis=1)
    if rate != 16000:
        a = np.interp(np.arange(0, len(a), rate / 16000), np.arange(len(a)), a)
    return a.astype(np.float32)


def transcribe(audio_bytes):
    try:
        audio = wav_to_array(audio_bytes)
    except Exception:                       # not WAV: fall back to faster-whisper's own decoder
        audio = io.BytesIO(audio_bytes)
    segments, _ = whisper().transcribe(audio, language="en")
    return " ".join(s.text for s in segments).strip()


def speech_text(text):
    """Turn a markdown answer into plain spoken sentences for gTTS."""
    t = text.replace("\\", "")                                    # stray backslashes
    t = re.sub(r"\((?:filters?|filter used)[^)]*\)", "", t, flags=re.I)  # filter lists: shown on screen, not read out
    t = re.sub(r"`([^`]*)`", r"\1", t)                            # inline code
    t = re.sub(r"\*\*|__|\*|#+ ?", "", t)                         # bold / italic / headings
    t = re.sub(r"^\s*(?:[-•]|\d+[.)])\s+", "", t, flags=re.M)    # bullet and number markers
    t = re.sub(r"\s*\n+\s*", ". ", t)                             # line breaks become pauses
    t = re.sub(r"(\w)_(\w)", r"\1 \2", t)                         # category_bridge -> category bridge
    t = re.sub(r"(\d)\s*[–-]\s*(\d)", r"\1 to \2", t)             # 6–10 -> 6 to 10
    t = re.sub(r"\d+\.\d+", lambda m: f"{round(float(m.group())):,}"
               if float(m.group()) >= 100 else m.group(), t)        # 7984.375 -> 7,984 ; keep 0.22
    t = re.sub(r"(?:S\$|\$)\s?([\d,]+)", r"\1 dollars", t)          # S$484 -> 484 dollars
    t = t.replace("/", " or ").replace("&", " and ")
    t = re.sub(r"[()\[\]{}|=<>]", " ", t)                          # leftover symbols
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)
    t = re.sub(r"([.!?:])\s*\.", r"\1", t)                         # ". ." and ":." doubles
    return re.sub(r"\s{2,}", " ", t).strip()


def speak(text):
    from gtts import gTTS
    buf = io.BytesIO()
    gTTS(text=speech_text(text), lang="en").write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- page
st.set_page_config(page_title="SGJobs AI Chat (local)", page_icon="🖥️")
st.title("🖥️ SGJobs AI Chat — local Hugging Face model")
st.caption(f"Model: {MODEL} via Ollama on Docker Desktop · no per-question cost · slower than the cloud version")

with st.sidebar:
    voice_reply = st.toggle("🔊 Read answers aloud (gTTS, needs internet)", value=False)
    show_plan = st.toggle("Show the model's raw plan", value=False)
    st.markdown("**Tips**\n- Speak or type naturally - no fixed questions.\n- Follow up: *same for Senior*, "
                "*only 2024*\n- Ask *how was this built?* or *what pages are there?*\n"
                "- Check any answer in the dashboard using the 🔧 filters shown.")

WELCOME = """**Hi, I'm the SGJobs analyst, running entirely on this computer** (a free Qwen model from Hugging Face, no
cloud AI). I work on about **1 million Singapore job postings (2023-2024)** through the same SGJobs API that powers the
dashboards, so every figure can be checked there.

**How the data was built:** Team 6 took the raw MyCareersFuture data (22 columns), cleaned and feature-engineered it in
Python into a validated table of 71 columns, and added two *bridge* tables so a job can belong to several Job Functions
and skills. The dashboard was built first in Power BI, then in Streamlit with 18 measures.

**What I can analyse (the 8 dashboard pages):** Overview · Salary (average vs median) · Opportunity Score ·
Demand & competition by seniority · Skills & Job Functions · Data quality & outliers · Reposting · Drill-through.

**Ask in your own words**, for example how the opportunity score is calculated, what mid-career IT managers earn, or
whether senior roles face less competition. Then follow up with *same for Senior* or *only 2024*. I'm slower than the
cloud version (about a minute per answer) because everything runs on this laptop's CPU."""

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


if not st.session_state.history:
    with st.chat_message("assistant"):
        st.markdown(WELCOME)

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
            if is_concept_question(question):
                with st.spinner("Explaining from Team 6's project documentation…"):
                    reply, background = answer_concept(question)
                path, filters, raw_plan = "(no API call: explained from project documentation)", {}, "concept question"
                notes, data = [], {"documentation used": background}
            else:
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
