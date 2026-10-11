"""SGJobs AI Chat - voice/text questions answered by Gemini, which calls the SGJobs FastAPI backend as tools."""
import io, os, re, json, hashlib
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
GLOSSARY = """
BUSINESS DEFINITIONS (from Team 6's Feature Engineering guide and presentation narrative; these override
general knowledge - never redefine them):

DATA MODEL
- Source: SGJobData (MyCareersFuture postings), 22 raw columns. Validated V3 analytical table: 1,044,597 rows x
  71 columns. The 49 added columns are NOT all business features: they are cleaned/standardised fields, engineered
  features, display bands, date helpers, percentile ranks, data-quality and review flags, plus pipeline_row_id.
  Families: Salary (salary_midpoint, salary_range, salary_range_pct, salary_band, salary_type_clean);
  Experience (experience_band); Vacancies (vacancy_band); Seniority (position_level_clean, seniority_group);
  Demand/competition (applications_per_vacancy, views_per_vacancy, application_rate); Job Function
  (category_primary, category_primary_id, category_count); Skills (title_clean, skill_tags, skill_count);
  Time/repost (posting_year/quarter/month/week/day/day_of_week, month_year, posting_duration_days, is_reposted);
  Quality (salary/range validity flags, duplicate_job_id, has_data_quality_issue, job_id_format,
  random_job_review_flag, salary_high_review_flag, experience_high_review_flag, vacancy_high_review_flag,
  vacancy_999_review_flag, needs_source_review); Opportunity (competition_rank_pct, vacancy_rank_pct,
  salary_rank_pct, opportunity_score, opportunity_band); employment_type_clean.
- Category (Job Function) bridge: one posting can have 1-5 employer-selected Job Functions (43 functions in
  total). The bridge stores one row per job-function pair (1,767,829 rows, no duplicate pairs) so secondary
  functions are not lost. A job ID repeating in the bridge is NOT a duplicate posting.
- category_primary = simply the FIRST function in the source list, a convenience field. List order is not proof
  the employer considered it primary. category_bridge is the recommended filter for official Job Function analysis.
- Skill bridge: skill_tags come from transparent keyword rules on the job TITLE (e.g. Python, Java, SQL, Data,
  Cloud, AWS, Azure, Cybersecurity, AI, Machine Learning, Software, Sales, Marketing, Accounting, Finance,
  Engineering). Not NLP - can miss synonyms. The skill bridge has one row per job-skill pair.
- Bridge counts use DISTINCT job IDs so a job with several functions/skills is counted once.

ENGINEERED COLUMNS
- salary_midpoint = (salary_minimum + salary_maximum) / 2: centre of the advertised range, NOT the salary paid.
  salary_range = max - min; salary_range_pct = range / midpoint.
- salary_band (from midpoint): < 3K, 3K-5K, 5K-7K, 7K-10K, 10K+. experience_band (minimum_years_experience):
  No experience required (0), 1-2, 3-5, 6-10, 10+ years. vacancy_band: 1 vacancy, 2-3, 4-10, 10+ vacancies.
- seniority_group: position level simplified to Entry Level (fresh/entry), Junior, Non-Executive, Senior,
  Manager, Professional, Executive, Other.
- applications_per_vacancy = applications / vacancies (applicant competition per opening);
  views_per_vacancy = views / vacancies (attention per opening); application_rate = applications / views
  (share of viewers who apply). These are observed platform activity, not proof of attractiveness.
- is_reposted = repost_count > 0. posting_duration_days = expiry date - posting date.
- has_data_quality_issue = any of: salary_minimum_invalid (<= 0), salary_maximum_invalid (<= 0),
  salary_range_invalid (max < min), duplicate_job_id. Review flags (salary_high_review_flag, vacancy_999_review_flag
  etc.) mark unusual but preserved values. Philosophy: preserve -> flag -> disclose -> verify with the data owner.
  Structural checks do not catch every implausible value (a huge positive salary can pass them).

OPPORTUNITY SCORE AND BAND
- Each input is turned into a 0-1 percentile rank because they are on different scales:
  competition_rank_pct = rank of applications_per_vacancy (near 1 = HIGH competition),
  vacancy_rank_pct = rank of number_of_vacancies, salary_rank_pct = rank of salary_midpoint.
- opportunity_score = (0.40 x (1 - competition_rank_pct) + 0.30 x vacancy_rank_pct + 0.30 x salary_rank_pct) x 100.
  Weights 40/30/30 are analyst choices, not machine learning. Example: competition 0.20, vacancy 0.80, salary 0.70
  -> 0.32 + 0.24 + 0.21 = 0.77 -> score 77.
- opportunity_band: Low (score <= 40), Moderate (40-60), Good (60-80), High (> 80; maximum in the data about 87).
  "Medium"/"average" opportunity means Moderate. There is no band called Medium.
- It is an exploratory screening index, NOT a prediction, probability of getting a job, or career advice.

THE 18 DASHBOARD MEASURES (Power BI DAX -> Python on the filtered rows)
 1 Total Job Postings (row count)            2 Unique Job Postings (distinct job IDs)
 3 Total Applications (sum)                  4 Total Vacancies (sum)
 5 Average Salary Midpoint                   6 Median Salary Midpoint (robust to outliers)
 7 Average Application Rate                  8 Average Applications per Vacancy (mean of job ratios)
 9 Average Views per Vacancy                10 Average Minimum Experience
11 Overall Applications per Vacancy = total applications / total vacancies (ratio of totals; differs from #8)
12 High Opportunity Jobs (distinct jobs in the High band)
13 Data Quality Issue Rate (share flagged)  14 Repost Rate (share reposted)
15 Distinct Categories                      16 Distinct Skills
17 Category Job Postings (distinct job IDs in the category bridge)
18 Skill Job Postings (distinct job IDs in the skill bridge)
Measures are recalculated for the current filters; columns are fixed per row.

INTERPRETATION RULES
- Always state the population ("within IT, senior roles, median salary is ...").
- Compare mean with median salary; a big gap suggests outliers or skew.
- Repost rate shows behaviour, not motive: say "consistent with possible recruitment difficulty", never
  "employers reposted because they could not find candidates".
- Use "shows / suggests / associated with"; avoid "proves / caused by".

ABOUT THE PROJECT (use this to answer "what can you do", "how was this built", "what pages/analyses are there"):
- Team 6 SGJobs project: Singapore job postings (MyCareersFuture data, 2023-2024). Raw SGJobData (22 columns) was
  cleaned and feature-engineered in Python into the validated V3 table (1,044,597 rows x 71 columns) plus two bridge
  tables. The dashboard was first built in Power BI, then migrated to Streamlit with 18 DAX-equivalent measures.
  This practice version splits it into a FastAPI backend (the SGJobs API) with Streamlit and React front ends on
  Google Cloud Run. This chatbot calls the SAME API, so its figures match the dashboards for the same filters.
- 8 dashboard pages (analyses) and the endpoint that serves each:
  1 Overview (overview): market size, employment types, top Job Functions, posting trends, vacancy rankings.
  2 Salary Analysis (salary): salary as a distribution - mean vs median, by function, seniority, experience.
  3 Opportunity Analysis (opportunity): the exploratory Opportunity Score and bands, and what drives them.
  4 Demand & Seniority (demand): vacancies vs applicant competition (applications/views per vacancy).
  5 Skills & Categories (skills_categories): Job Functions via the bridge, title-keyword skills.
  6 Data Quality & Outliers (data_quality): review flags; preserve -> flag -> investigate -> verify.
  7 Repost Analysis (repost): repost rate; observed behaviour, not employer motive.
  8 Detail Drillthrough (get_job_details): one job's source values, derived fields, functions and skills.
- Sidebar filters (the "population"): employment type, Job Function (primary or bridge), skill, seniority,
  experience band, vacancy band, salary band, opportunity band, posting year.
- Investigation method: define the population -> measure -> compare -> investigate -> validate -> qualify.
  Workflow A "Is a Job Function truly high opportunity?": check scale (overview), score drivers (opportunity),
  vacancies and competition (demand), mean vs median salary (salary), flags (data_quality).
  Workflow B "Is a high-salary category genuinely high-paying?": compare mean and median, check outliers
  (data_quality), check seniority/experience mix, then conclude.

ROUTING RULES:
- "high / good / moderate (medium) / low opportunity" -> endpoint "opportunity" (or the endpoint the question needs)
  WITH opportunity_band filter set to that band. Never judge opportunity from average salary.
- "high-paying / high salary" -> salary_band, not opportunity_band.
- "Job Function" questions -> prefer the category_bridge filter (official, all functions); category_primary only
  if the user asks for the primary/first category.
- "Skill" questions -> skill_bridge filter.
- Questions about a measure (e.g. repost rate, applications per vacancy) -> call the endpoint that returns it
  and say which measure it is (e.g. average of job ratios vs ratio of totals).
- If a term is not defined here and has no matching filter, say so instead of inventing a rule.
- In the answer, name the filter you used, e.g. "(filter: opportunity_band = High)".
"""
CALLS = []                         # log of tool calls for the current question (shown in the UI)


def _get(path, params=None):
    params = {k: v for k, v in (params or {}).items() if v not in (None, [], "")}
    r = requests.get(API + path, params=params, timeout=120)
    r.raise_for_status()
    text = json.dumps(r.json(), default=str)
    CALLS.append({"path": path, "filters": params})
    if len(text) > 60000:          # very large reply: keep most of it and say so, never cut silently
        return text[:60000] + ' ... [TRUNCATED: tell the user part of the data was not read]'
    return text


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
        salary_band: salary bands only; use only for questions about pay level.
        opportunity_band: Low, Moderate, Good or High band of opportunity_score (0-100, combining high
            salary, low demand and high vacancies). "High opportunity" = score 80+ = the High band.
            Use this filter for any opportunity question; never use average salary for it.
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
    raw = requests.get(API + "/api/filters", timeout=120).json()
    if isinstance(raw, dict) and "filters" in raw:
        raw = raw["filters"]
    if isinstance(raw, list):                          # API shape: [{"param": ..., "options": [...]}, ...]
        raw = {f["param"]: f.get("options", []) for f in raw if isinstance(f, dict) and "param" in f}
    if not isinstance(raw, dict):
        return json.dumps(raw, default=str)[:30000]
    lines = []
    for key, vals in raw.items():                      # one line per filter, so no key is ever cut off
        vals = vals if isinstance(vals, list) else [vals]
        shown = vals[:80]
        more = f" ... (+{len(vals) - 80} more)" if len(vals) > 80 else ""
        lines.append(f"- {key}: " + json.dumps(shown, default=str, ensure_ascii=False) + more)
    return "\n".join(lines)


def transcribe(audio_bytes, mime):
    r = llm().models.generate_content(
        model=MODEL,
        contents=[types.Part.from_bytes(data=audio_bytes, mime_type=mime),
                  "Transcribe this audio exactly. Return only the transcript."])
    return (r.text or "").strip()


def ask_ai(history):
    system = (
        "You are an SGJobs labour-market analyst who reasons like Team 6's dashboard method, not a lookup box.\n"
        "DATA vs MEANING: for figures (counts, salaries, rates, trends) ALWAYS call query_sgjobs (or "
        "get_job_details) - never give figures from memory. For what a term MEANS, how a score is calculated, how "
        "the data was built, or what the pages/analyses are, answer from the definitions and ABOUT THE PROJECT "
        "below without a tool.\n"
        "INVESTIGATE: when a question asks whether something is 'really', 'genuinely', 'truly' true, or asks why, "
        "do a short investigation with SEVERAL tool calls (e.g. Workflow A or B): compare against the overall "
        "market or another segment, compare mean with median, check what drives a score, check data-quality flags. "
        "Then give a qualified conclusion.\n"
        "BE PROACTIVE: end every data answer with one short observation the user may not have noticed (e.g. a big "
        "mean-median gap, a small sample, bridge vs primary difference) and ONE suggested next question, written "
        "as a natural sentence the user can answer in their own words.\n"
        "FOLLOW-UPS: if the user says 'now for Senior', 'what about 2024', 'why', etc., keep the filters from the "
        "previous question and change only what they asked.\n"
        "FILTERS: use ONLY exact filter values from the list below; if a value doesn't match, pick the closest "
        "valid one and say which you used. For Job Function prefer category_bridge and say so. Always state the "
        "population the figures describe and list the filters used.\n"
        "STYLE: quote numbers exactly as returned; never invent figures; 2-5 sentences for simple questions, up "
        "to about 8 for investigations; salaries are in SGD; use 'shows / suggests / associated with', never "
        "'proves / caused by'. If a list of individual jobs is asked for and no tool returns one, say so briefly "
        "and give the summary figures for that population instead.\n"
        + GLOSSARY + "\nVALID FILTER VALUES:\n" + valid_filters())
    contents = [types.Content(role="user" if m["role"] == "user" else "model",
                              parts=[types.Part(text=m["content"])]) for m in history[-8:]]
    r = llm().models.generate_content(
        model=MODEL, contents=contents,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.1,
                                           tools=[query_sgjobs, get_job_details]))
    return (r.text or "Sorry, I couldn't produce an answer.").strip()


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
    buf = io.BytesIO()
    gTTS(text=speech_text(text), lang="en").write_to_fp(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- page
st.set_page_config(page_title="SGJobs AI Chat", page_icon="🎙️")
st.title("🎙️ SGJobs AI Chat")
st.caption("Ask by voice or text, in your own words. The AI chooses the SGJobs API endpoints and filters itself - no slicers.")

WELCOME = """**Hi, I'm the SGJobs analyst.** I work on about **1 million Singapore job postings (2023-2024)** and call the same
SGJobs API that powers the dashboards, so you can check every figure I give you.

**How the data was built:** Team 6 took the raw MyCareersFuture data (22 columns), cleaned and feature-engineered it in
Python into a validated table of 71 columns, and added two *bridge* tables so a job can belong to several Job Functions
and skills. The dashboard was built first in Power BI, then in Streamlit with 18 measures.

**What I can analyse (the 8 dashboard pages):** Overview of the market · Salary (average vs median) · Opportunity Score ·
Demand & competition by seniority · Skills & Job Functions · Data quality & outliers · Reposting · Drill-through to a single job.

**Ask me anything, in your own words.** For example, you could:
- ask how something was built: *how is the opportunity score calculated, or why are there bridge tables?*
- measure a group: *what do mid-career IT managers earn?*
- compare: *do senior roles face less competition than entry-level ones?*
- challenge a result: *is Banking really high-paying, or is the average skewed?*
- follow up: *now only 2024*, *same for Senior*, *why is that?*

I'll tell you which filters I used, point out anything unusual, and suggest what to look at next."""

with st.sidebar:
    voice_reply = st.toggle("🔊 Read answers aloud", value=True)
    st.markdown("**Tips**\n- Speak or type naturally - no fixed questions.\n- Follow up: *same for Senior*, "
                "*only 2024*, *why?*\n- Ask *how was this built?* or *what pages are there?*\n"
                "- Check any answer in the dashboard using the 🔧 filters shown.")

st.session_state.setdefault("history", [])
st.session_state.setdefault("last_audio", None)

if not st.session_state.history:
    with st.chat_message("assistant"):
        st.markdown(WELCOME.replace("$", r"\$"))

for m in st.session_state.history:
    with st.chat_message(m["role"]):
        st.markdown(m["content"].replace("$", r"\$"))
        for c in m.get("calls", []):
            st.caption(f"🔧 {c['path']}  {c['filters'] or '(no filters)'}")

question = None
audio = st.audio_input("🎙️ Ask by voice")
if audio is not None:
    audio_bytes = audio.getvalue()
    if len(audio_bytes) > 3_000_000:                 # roughly 30-60 s of audio
        st.warning("Please keep voice questions under about 30 seconds.")
        st.stop()
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
        st.markdown(answer.replace("$", r"\$"))
        calls = list(CALLS)
        for c in calls:
            st.caption(f"🔧 {c['path']}  {c['filters'] or '(no filters)'}")
        if voice_reply:
            st.audio(speak(answer), format="audio/mp3", autoplay=True)
    st.session_state.history.append({"role": "assistant", "content": answer, "calls": calls})
