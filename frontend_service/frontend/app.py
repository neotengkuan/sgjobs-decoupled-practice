"""
SGJobs decoupled practice - frontend (Streamlit).

Start the backend first, then this app:

    # terminal 1 (project root)
    uvicorn backend.main:app --reload --port 8000

    # terminal 2 (project root)
    streamlit run frontend/app.py

WHAT THIS FILE OWNS
------------------
* Rendering the sidebar filter widgets described by the API.
* Sending the selected values as query parameters.
* Formatting and laying out the KPI cards.
* Drawing the Overview, Salary Analysis, Opportunity Analysis, Demand &
  Seniority and Skills & Categories charts, plus the Data Quality &
  Outliers, Repost Analysis and Detail Drillthrough tables, from the
  returned JSON.

It contains no filtering or aggregation logic: no mask, no groupby, no
parquet, no pandas. GET /api/filters says which filters exist and what
they may contain, GET /api/overview applies the selection and returns the
KPIs, and the tab endpoints return pre-aggregated datasets.
app_deploy.py stays untouched as the reference version to compare
against.
"""

from __future__ import annotations

import os
from urllib.parse import quote, urlencode

import altair as alt
import requests
import streamlit as st

# ============================================================
# PAGE SETTINGS
# ============================================================
# Must stay the first Streamlit command in the script.

st.set_page_config(
    page_title="SGJobs Interactive Dashboard",
    page_icon="💼",
    layout="wide",
)


# ============================================================
# API CONNECTION
# ============================================================
# Override with an environment variable when the API is not local:
#   $env:SGJOBS_API_URL = "https://sgjobs-api.example.com"

API_BASE_URL = os.getenv(
    "SGJOBS_API_URL",
    "http://localhost:8000",
).rstrip("/")

REQUEST_TIMEOUT = float(os.getenv("SGJOBS_API_TIMEOUT", "600"))

OVERVIEW_URL = f"{API_BASE_URL}/api/overview"
CHARTS_URL = f"{API_BASE_URL}/api/overview/charts"
SALARY_URL = f"{API_BASE_URL}/api/salary/analysis"
OPPORTUNITY_URL = f"{API_BASE_URL}/api/opportunity/analysis"
DEMAND_URL = f"{API_BASE_URL}/api/demand/analysis"
BRIDGE_URL = f"{API_BASE_URL}/api/skills-categories/analysis"
QUALITY_URL = f"{API_BASE_URL}/api/data-quality/analysis"
REPOST_URL = f"{API_BASE_URL}/api/repost/analysis"
JOBS_URL = f"{API_BASE_URL}/api/jobs"
JOB_IDS_URL = f"{API_BASE_URL}/api/jobs/ids"
FILTERS_URL = f"{API_BASE_URL}/api/filters"
HEALTH_URL = f"{API_BASE_URL}/api/health"

# The first request pays for the parquet load, so keep the frontend
# cache short enough that a restarted backend is picked up quickly.
API_CACHE_TTL = int(os.getenv("SGJOBS_API_CACHE_TTL", "300"))

# The drillthrough controls, mirroring app_deploy.py: the "Rows to
# display" options and its default at index 2.
ROWS_TO_SHOW_OPTIONS = [25, 50, 100, 250, 500]
ROWS_TO_SHOW_DEFAULT = 100

# Cap on the job-id selector options, matching the backend and the
# reference's head(10_000).
JOB_ID_LIMIT = 10000

# The filter options only change when the source data changes, so they can
# be cached for much longer than the KPI responses.
FILTER_CACHE_TTL = int(os.getenv("SGJOBS_FILTER_CACHE_TTL", "3600"))


# ============================================================
# FORMATTERS
# ============================================================
# Same output as app_deploy.py's fmt_number / fmt_currency /
# fmt_percent. The API sends null for missing measures, which these
# helpers render as "N/A" just like pandas.isna did before.


def fmt_number(value):
    if value is None:
        return "N/A"
    return f"{value:,.0f}"


def fmt_currency(value):
    if value is None:
        return "N/A"
    return f"S${value:,.0f}"


def fmt_percent(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def fmt_decimal(value, places=1, suffix=""):
    if value is None:
        return "N/A"
    return f"{value:.{places}f}{suffix}"


# ============================================================
# API CALL
# ============================================================

@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_job_detail(url, timeout):
    """GET one job's detail record (the first matching filtered row)."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_job_bridge(url, timeout):
    """GET one job's category- or skill-bridge rows."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_job_ids(url, timeout):
    """GET the job-id selector options for the current filter selection."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_jobs(url, timeout):
    """GET one page of matching job records."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_repost_analysis(url, timeout):
    """
    GET the pre-aggregated Repost Analysis datasets for one filter
    selection. Cached per URL like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_quality_analysis(url, timeout):
    """
    GET the pre-aggregated Data Quality & Outliers datasets, including
    the capped review rows for one review population. Cached per URL
    like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_demand_analysis(url, timeout):
    """
    GET the pre-aggregated Demand & Seniority tab datasets, including
    the capped scatter sample. Cached per URL like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_bridge_analysis(url, timeout):
    """
    GET the pre-aggregated Skills & Categories (bridge) tab datasets.
    Cached per URL like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_opportunity_analysis(url, timeout):
    """
    GET the pre-aggregated Opportunity Analysis tab datasets for one
    filter selection. Cached per URL like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_salary_analysis(url, timeout):
    """
    GET the pre-aggregated Salary Analysis tab datasets for one filter
    selection. Cached per URL like the other endpoints.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_overview_charts(url, timeout):
    """
    GET the pre-aggregated Overview chart datasets for one filter
    selection. Cached per URL like the KPIs.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=API_CACHE_TTL, show_spinner=False)
def fetch_overview(url, timeout):
    """GET the Overview KPIs for one filter selection. Cached per URL."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=FILTER_CACHE_TTL, show_spinner=False)
def fetch_filters(url, timeout):
    """GET the sidebar descriptors (labels, option lists) from the API."""
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=30, show_spinner=False)
def fetch_health(url, timeout):
    """Used only for a clearer error message when the API is unreachable."""
    response = requests.get(url, timeout=min(timeout, 5))
    response.raise_for_status()
    return response.json()


def build_api_url(base_url, selections, extra_pairs=None):
    """
    Turn the user's selections into a query string.

    One repeated query parameter per selected value, e.g.
    ?salary_band=5K%E2%80%937K&posting_year=2025&posting_year=2026

    extra_pairs adds one-off parameters, e.g. the review population.

    The finished URL is the cache key for the fetchers above, so
    identical selections reuse the same response.
    """
    pairs = [
        (param, value)
        for param, values in selections.items()
        for value in values
    ]

    pairs.extend(extra_pairs or [])

    if not pairs:
        return base_url

    return f"{base_url}?{urlencode(pairs)}"


def stop_with_api_error(error, what="Could not reach the SGJobs API."):
    st.error(what)

    st.code(
        f"API URL : {API_BASE_URL}\n"
        f"Error   : {type(error).__name__}: {error}",
        language="text",
    )

    st.markdown(
        "Start the backend from the project root, in a second terminal:\n\n"
        "```\n"
        "uvicorn backend.main:app --reload --port 8000\n"
        "```\n\n"
        "The first start loads the parquet file, so it can take a while. "
        "Then reload this page."
    )

    st.stop()


def call_api(fetcher, *args):
    """
    Run one of the cached fetchers and turn any failure into the same
    message, so every endpoint is called the same way.
    """
    try:
        return fetcher(*args)

    except requests.exceptions.ConnectionError as error:
        stop_with_api_error(error)

    except requests.exceptions.Timeout as error:
        stop_with_api_error(error)

    except requests.exceptions.HTTPError as error:
        detail = ""

        try:
            detail = error.response.json().get("detail", "")
        except (AttributeError, ValueError):
            detail = getattr(error.response, "text", "")

        st.error(f"The API returned an error: {detail or error}")

        if (
            error.response is not None
            and error.response.status_code == 422
        ):
            st.warning(
                "The API rejected one of the current filter values. "
                "Press Reset Filters, then try again."
            )

        st.stop()

    except ValueError as error:
        stop_with_api_error(
            error,
            "The API replied, but not with valid JSON.",
        )


# ============================================================
# PAGE HEADER
# ============================================================

st.title("💼 SGJobs Interactive Dashboard")
st.caption(
    "V3 baseline: 1,044,597 validated logical records | "
    "Expanded Power BI-equivalent analysis + multi-label bridges"
)
st.caption(
    "Decoupled build: filters, KPIs and tab data are served by the "
    "FastAPI backend; app_deploy.py remains the untouched reference version."
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================
# The backend owns the filter definitions: labels, option lists, option
# ordering and the mask itself. This block only renders the widgets it
# hands over and remembers what the user selected.

st.sidebar.header("Filters")

filter_specs = call_api(
    fetch_filters,
    FILTERS_URL,
    REQUEST_TIMEOUT,
).get("filters", [])


def reset_filters():
    """Clear every filter widget, same behaviour as app_deploy.py."""
    for spec in filter_specs:
        st.session_state[spec["state_key"]] = []


selections = {}

for spec in filter_specs:
    # The backend marks a filter unavailable when the loaded data has
    # no such column/table; app_deploy.py hides those widgets too.
    if not spec.get("available"):
        continue

    selected = st.sidebar.multiselect(
        spec["label"],
        options=spec.get("options", []),
        key=spec["state_key"],
        help=spec.get("help"),
    )

    selections[spec["param"]] = selected


unavailable = [
    spec["label"]
    for spec in filter_specs
    if not spec.get("available")
]

if unavailable:
    st.sidebar.caption(
        "Unavailable in this dataset: " + ", ".join(unavailable)
    )


st.sidebar.button(
    "Reset Filters",
    on_click=reset_filters,
)

st.sidebar.divider()

if st.sidebar.button("Refresh API data", type="primary"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(f"API: {API_BASE_URL}")


# ============================================================
# FETCH OVERVIEW DATA FOR THE CURRENT SELECTION
# ============================================================
# The same selections drive both endpoints, so the KPI cards and the
# Overview charts always describe the same filtered rows.

overview_url = build_api_url(OVERVIEW_URL, selections)
charts_url = build_api_url(CHARTS_URL, selections)
salary_url = build_api_url(SALARY_URL, selections)
opportunity_url = build_api_url(OPPORTUNITY_URL, selections)
demand_url = build_api_url(DEMAND_URL, selections)
bridge_url = build_api_url(BRIDGE_URL, selections)

# The review population is read before the selectbox is rendered,
# because the API response supplies the data shown above it. On the
# first render there is nothing selected yet, so nothing is sent and the
# backend applies its own default (the first option).
selected_review_population = st.session_state.get(
    "outlier_review_population"
)

quality_pairs = (
    [("review_population", selected_review_population)]
    if selected_review_population
    else []
)

quality_url = build_api_url(QUALITY_URL, selections, quality_pairs)
repost_url = build_api_url(REPOST_URL, selections)

payload = call_api(fetch_overview, overview_url, REQUEST_TIMEOUT)

meta = payload.get("meta", {})
primary = payload.get("primary_kpis", {})
bridge = payload.get("bridge_kpis", {})
dax = payload.get("dax_measures", {})


st.caption(
    f"Optimized source: {meta.get('data_file', 'unknown')} "
    f"({meta.get('source_type', 'unknown')})  |  "
    f"Rows loaded: {fmt_number(meta.get('rows_total'))}  |  "
    f"Columns loaded: {fmt_number(len(meta.get('columns_loaded', [])))}"
)


# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Total Jobs",
    fmt_number(primary.get("total_jobs")),
)

k2.metric(
    "Average Salary",
    fmt_currency(primary.get("average_salary")),
)

k3.metric(
    "Median Salary",
    fmt_currency(primary.get("median_salary")),
)

k4.metric(
    "Total Vacancies",
    fmt_number(primary.get("total_vacancies")),
)

k5.metric(
    "Avg Opportunity Score",
    fmt_decimal(primary.get("avg_opportunity"), places=1),
)

st.caption(
    f"Showing {fmt_number(meta.get('rows_filtered'))} of "
    f"{fmt_number(meta.get('rows_total'))} job records"
)
st.caption(meta.get("filter_context", ""))


bridge_k1, bridge_k2, bridge_k3, bridge_k4 = st.columns(4)

bridge_k1.metric(
    "Distinct Categories",
    fmt_number(bridge.get("distinct_categories")),
)

bridge_k2.metric(
    "Category Job Postings",
    fmt_number(bridge.get("category_job_postings")),
)

bridge_k3.metric(
    "Distinct Skills",
    fmt_number(bridge.get("distinct_skills")),
)

bridge_k4.metric(
    "Skill Job Postings",
    fmt_number(bridge.get("skill_job_postings")),
)


with st.expander("Power BI / DAX-equivalent measures", expanded=False):
    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Unique Job Postings",
        fmt_number(dax.get("unique_job_postings")),
    )

    m2.metric(
        "Total Applications",
        fmt_number(dax.get("total_applications")),
    )

    m3.metric(
        "Overall Applications / Vacancy",
        fmt_decimal(
            dax.get("overall_applications_per_vacancy"),
            places=2,
        ),
    )

    m4.metric(
        "High Opportunity Jobs",
        fmt_number(dax.get("high_opportunity_jobs")),
    )

    m5, m6, m7, m8 = st.columns(4)

    m5.metric(
        "Average Application Rate",
        fmt_percent(dax.get("average_application_rate")),
    )

    m6.metric(
        "Average Applications / Vacancy",
        fmt_decimal(
            dax.get("average_applications_per_vacancy"),
            places=2,
        ),
    )

    m7.metric(
        "Average Views / Vacancy",
        fmt_decimal(
            dax.get("average_views_per_vacancy"),
            places=2,
        ),
    )

    m8.metric(
        "Average Minimum Experience",
        fmt_decimal(
            dax.get("average_minimum_experience"),
            places=1,
            suffix=" years",
        ),
    )

    m9, m10 = st.columns(2)

    m9.metric(
        "Data Quality Issue Rate",
        fmt_percent(dax.get("data_quality_issue_rate")),
    )

    m10.metric(
        "Repost Rate",
        fmt_percent(dax.get("repost_rate")),
    )


# ============================================================
# TABS
# ============================================================
# Every tab of app_deploy.py is decoupled: Overview, Salary Analysis,
# Opportunity Analysis, Demand & Seniority, Skills & Categories, Data
# Quality & Outliers, Repost Analysis and Detail Drillthrough.

(
    overview_tab,
    salary_tab,
    opportunity_tab,
    demand_tab,
    bridge_tab,
    quality_tab,
    repost_tab,
    records_tab,
) = st.tabs(
    [
        "📊 Overview",
        "💰 Salary Analysis",
        "🎯 Opportunity Analysis",
        "📈 Demand & Seniority",
        "🧩 Skills & Categories",
        "🧪 Data Quality & Outliers",
        "🔁 Repost Analysis",
        "📋 Detail Drillthrough",
    ]
)


# ============================================================
# OVERVIEW
# ============================================================
# Every dataset below is aggregated by the backend from the currently
# filtered rows. This block only draws the charts; the Altair encodings
# match app_deploy.py so the rendered charts are identical.

charts_payload = call_api(fetch_overview_charts, charts_url, REQUEST_TIMEOUT)

charts = charts_payload.get("charts", {})

with overview_tab:

    col_left, col_right = st.columns(2)

    # Jobs by Employment Type
    with col_left:
        st.subheader("Jobs by Employment Type")

        employment_chart = charts.get("employment_type", {})

        if employment_chart.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=employment_chart.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Employment Type:N",
                        sort="-y",
                        axis=alt.Axis(labelAngle=-30),
                    ),
                    y=alt.Y(
                        "Jobs:Q",
                        title="Number of Jobs",
                    ),
                    tooltip=[
                        alt.Tooltip("Employment Type:N"),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=340)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    # Top Job Functions
    with col_right:
        st.subheader("Top 15 Job Functions")

        job_functions_chart = charts.get("top_job_functions", {})

        if job_functions_chart.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=job_functions_chart.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Jobs:Q",
                        title="Number of Jobs",
                    ),
                    y=alt.Y(
                        "Job Function:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Job Function:N"),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=400)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    col_left2, col_right2 = st.columns(2)

    # Jobs Over Time
    with col_left2:
        st.subheader("Jobs Over Time")

        over_time_chart = charts.get("jobs_over_time", {})

        if over_time_chart.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=over_time_chart.get("data", []),
                    )
                )
                .mark_line(point=True)
                .encode(
                    x=alt.X(
                        "month_year:N",
                        title="Month",
                        sort=None,
                        axis=alt.Axis(labelAngle=-45),
                    ),
                    y=alt.Y(
                        "Jobs:Q",
                        title="Number of Jobs",
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "month_year:N",
                            title="Month",
                        ),
                        alt.Tooltip(
                            "Jobs:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(height=340)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    # Top Functions by Vacancies
    with col_right2:
        st.subheader("Top 10 Job Functions by Vacancies")

        vacancies_chart = charts.get(
            "top_job_functions_by_vacancies",
            {},
        )

        if vacancies_chart.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=vacancies_chart.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Vacancies:Q",
                        title="Total Vacancies",
                    ),
                    y=alt.Y(
                        "Job Function:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Job Function:N"),
                        alt.Tooltip(
                            "Vacancies:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(height=400)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )


# ============================================================
# SALARY ANALYSIS
# ============================================================
# Same pattern as the Overview tab: the backend does the aggregation
# and sends small datasets, this block only draws them. The Altair
# encodings and the summary table match app_deploy.py.

salary_payload = call_api(fetch_salary_analysis, salary_url, REQUEST_TIMEOUT)

salary_band_counts = salary_payload.get("salary_band_counts", {})
salary_by_function = salary_payload.get(
    "average_salary_by_job_function",
    {},
)
salary_summary = salary_payload.get("summary", {})


with salary_tab:

    salary_left, salary_right = st.columns(2)

    with salary_left:
        st.subheader("Jobs by Salary Band")

        if salary_band_counts.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=salary_band_counts.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Salary Band:N",
                        title="Salary Band",
                        sort=[
                            "< 3K",
                            "3K–5K",
                            "5K–7K",
                            "7K–10K",
                            "10K+",
                            "Unknown",
                        ],
                    ),
                    y=alt.Y(
                        "Jobs:Q",
                        title="Number of Jobs",
                    ),
                    tooltip=[
                        alt.Tooltip("Salary Band:N"),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=340)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    with salary_right:
        st.subheader("Average Salary by Job Function")

        if salary_by_function.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=salary_by_function.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Average Salary:Q",
                        title="Average Salary (S$)",
                    ),
                    y=alt.Y(
                        "Job Function:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Job Function:N"),
                        alt.Tooltip(
                            "Average Salary:Q",
                            format=",.0f",
                        ),
                    ],
                )
                .properties(height=420)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    st.subheader("Salary Summary")

    if salary_summary.get("available"):
        st.dataframe(
            [
                {
                    "Measure": "Jobs with salary data",
                    "Value": fmt_number(
                        salary_summary.get("jobs_with_salary_data")
                    ),
                },
                {
                    "Measure": "Average salary",
                    "Value": fmt_currency(
                        salary_summary.get("average_salary")
                    ),
                },
                {
                    "Measure": "Median salary",
                    "Value": fmt_currency(
                        salary_summary.get("median_salary")
                    ),
                },
                {
                    "Measure": "Minimum salary midpoint",
                    "Value": fmt_currency(
                        salary_summary.get("minimum_salary_midpoint")
                    ),
                },
                {
                    "Measure": "Maximum salary midpoint",
                    "Value": fmt_currency(
                        salary_summary.get("maximum_salary_midpoint")
                    ),
                },
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# OPPORTUNITY ANALYSIS
# ============================================================
# The backend averages the pre-computed opportunity_score column; no
# score is recalculated here. The ranking decision (sample-size floor,
# whether the fallback was used) comes back with the rows so the
# reference caption for that branch can be reproduced.

opportunity_payload = call_api(
    fetch_opportunity_analysis,
    opportunity_url,
    REQUEST_TIMEOUT,
)

opportunity_bands = opportunity_payload.get(
    "opportunity_band_counts",
    {},
)
opportunity_ranking = opportunity_payload.get("top_job_functions", {})


with opportunity_tab:

    st.caption(
        "Opportunity Score is exploratory/indicative, "
        "not a validated predictive model."
    )

    opp_left, opp_right = st.columns(2)

    with opp_left:
        st.subheader("Jobs by Opportunity Band")

        if opportunity_bands.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=opportunity_bands.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Opportunity Band:N",
                        sort=[
                            "Low",
                            "Moderate",
                            "Good",
                            "High",
                        ],
                    ),
                    y=alt.Y(
                        "Jobs:Q",
                        title="Number of Jobs",
                    ),
                    tooltip=[
                        alt.Tooltip("Opportunity Band:N"),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=340)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    with opp_right:
        st.subheader("Top Job Functions by Opportunity Score")

        if opportunity_ranking.get("available"):

            if opportunity_ranking.get("fallback_applied"):
                st.caption(
                    "No job function met the minimum sample-size rule for "
                    "this filter selection, so all available functions are shown."
                )
            else:
                st.caption(
                    "Ranking uses job functions with at least "
                    f"{fmt_number(opportunity_ranking.get('min_jobs'))} "
                    "matching jobs."
                )

            chart = (
                alt.Chart(
                    alt.Data(
                        values=opportunity_ranking.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Average Opportunity Score:Q",
                        title="Average Opportunity Score",
                    ),
                    y=alt.Y(
                        "Job Function:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Job Function:N"),
                        alt.Tooltip(
                            "Average Opportunity Score:Q",
                            format=".1f",
                        ),
                        alt.Tooltip(
                            "Jobs:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(height=420)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )


# ============================================================
# DEMAND & SENIORITY
# ============================================================
# Two aggregated bar charts plus the scatter plot. The scatter is
# row-level by nature; the backend caps and seeds it and reports which
# fields survived, so the reference's conditional tooltips are rebuilt
# here without the frontend inspecting the data.

demand_payload = call_api(fetch_demand_analysis, demand_url, REQUEST_TIMEOUT)

seniority_counts = demand_payload.get("seniority_counts", {})
seniority_salary = demand_payload.get("average_salary_by_seniority", {})
scatter = demand_payload.get("salary_vs_applications", {})


with demand_tab:

    st.caption(
        "Demand measures mirror the Power BI business view. "
        "The scatter plot is descriptive; it does not imply causation."
    )

    demand_left, demand_right = st.columns(2)

    with demand_left:
        st.subheader("Jobs by Seniority")

        if seniority_counts.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=seniority_counts.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Jobs:Q",
                        title="Job Postings",
                    ),
                    y=alt.Y(
                        "Seniority:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Seniority:N"),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=360)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    with demand_right:
        st.subheader("Average Salary by Seniority")

        if seniority_salary.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=seniority_salary.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Average Salary:Q",
                        title="Average Salary (S$)",
                    ),
                    y=alt.Y(
                        "Seniority:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Seniority:N"),
                        alt.Tooltip(
                            "Average Salary:Q",
                            format=",.0f",
                        ),
                        alt.Tooltip(
                            "Median Salary:Q",
                            format=",.0f",
                        ),
                        alt.Tooltip("Jobs:Q", format=","),
                    ],
                )
                .properties(height=360)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

    st.subheader("Salary vs Applications per Vacancy")

    if scatter.get("available"):

        if scatter.get("sampled"):
            st.caption(
                "Scatter plot displays a reproducible "
                f"{fmt_number(scatter.get('rows_sampled'))}-row sample "
                "for browser performance; dashboard measures still use "
                "all filtered rows."
            )

        # The backend reports which fields it actually sent, so the
        # reference's conditional tooltip list can be rebuilt as-is.
        scatter_fields = scatter.get("fields", [])

        tooltip_fields = []

        if "metadata_job_post_id" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "metadata_job_post_id:N",
                    title="Job ID",
                )
            )

        if "category_primary" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "category_primary:N",
                    title="Job Function (compat.)",
                )
            )

        if "seniority_group" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "seniority_group:N",
                    title="Seniority",
                )
            )

        tooltip_fields.extend(
            [
                alt.Tooltip(
                    "salary_midpoint:Q",
                    title="Salary midpoint",
                    format=",.0f",
                ),
                alt.Tooltip(
                    "number_of_vacancies:Q",
                    title="Vacancies",
                    format=",",
                ),
                alt.Tooltip(
                    "applications_per_vacancy:Q",
                    title="Applications / vacancy",
                    format=".2f",
                ),
            ]
        )

        if "views_per_vacancy" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "views_per_vacancy:Q",
                    title="Views / vacancy",
                    format=".2f",
                )
            )

        if "application_rate" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "application_rate:Q",
                    title="Application rate",
                    format=".2%",
                )
            )

        if "opportunity_score" in scatter_fields:
            tooltip_fields.append(
                alt.Tooltip(
                    "opportunity_score:Q",
                    title="Opportunity score",
                    format=".1f",
                )
            )

        chart = (
            alt.Chart(
                alt.Data(
                    values=scatter.get("data", []),
                )
            )
            .mark_circle(opacity=0.45)
            .encode(
                x=alt.X(
                    "applications_per_vacancy:Q",
                    title="Applications per Vacancy",
                    scale=alt.Scale(zero=False),
                ),
                y=alt.Y(
                    "salary_midpoint:Q",
                    title="Salary Midpoint (S$)",
                    scale=alt.Scale(zero=False),
                ),
                size=alt.Size(
                    "number_of_vacancies:Q",
                    title="Vacancies",
                    scale=alt.Scale(range=[15, 600]),
                ),
                color=(
                    alt.Color(
                        "seniority_group:N",
                        title="Seniority",
                    )
                    if "seniority_group" in scatter_fields
                    else alt.value("#4C78A8")
                ),
                tooltip=tooltip_fields,
            )
            .properties(height=500)
            .interactive()
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )


# ============================================================
# SKILLS & CATEGORIES
# ============================================================
# Bridge datasets: the backend joins the bridge tables to the filtered
# job-id set and ranks by DISTINCT job postings, so multi-label rows
# never double-count a job.

bridge_payload = call_api(fetch_bridge_analysis, bridge_url, REQUEST_TIMEOUT)

top_categories = bridge_payload.get("top_categories", {})
top_skills = bridge_payload.get("top_skills", {})


with bridge_tab:

    st.caption(
        "These visuals use the separate bridge tables. "
        "For official multi-label Job Function analysis, use the category bridge. "
        "category_primary remains only for compatibility with the existing slicer."
    )

    bridge_left, bridge_right = st.columns(2)

    with bridge_left:
        st.subheader("Top Categories by Job Postings")

        if top_categories.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=top_categories.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Job Postings:Q",
                        title="Unique Job Postings",
                    ),
                    y=alt.Y(
                        "Category:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Category:N"),
                        alt.Tooltip(
                            "Job Postings:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(height=420)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

        else:
            st.info(
                "Category bridge is unavailable "
                "or expected columns are missing."
            )

    with bridge_right:
        st.subheader("Top Skills by Job Postings")

        if top_skills.get("available"):
            chart = (
                alt.Chart(
                    alt.Data(
                        values=top_skills.get("data", []),
                    )
                )
                .mark_bar()
                .encode(
                    x=alt.X(
                        "Job Postings:Q",
                        title="Unique Job Postings",
                    ),
                    y=alt.Y(
                        "Skill:N",
                        sort="-x",
                    ),
                    tooltip=[
                        alt.Tooltip("Skill:N"),
                        alt.Tooltip(
                            "Job Postings:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(height=420)
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

        else:
            st.info(
                "Skill bridge is unavailable "
                "or expected columns are missing."
            )


# ============================================================
# DATA QUALITY & OUTLIERS
# ============================================================
# Three metric-card counts, the Team 6 review-rule table and the
# capped review table come from the API. Data Quality Issue Rate is
# deliberately NOT recomputed here: app_deploy.py computes it once and
# reuses it in the DAX expander and on this tab, so the value below is
# read from the already-fetched overview payload.

quality_payload = call_api(
    fetch_quality_analysis,
    quality_url,
    REQUEST_TIMEOUT,
)

quality_meta = quality_payload.get("meta", {})
quality_kpis = quality_payload.get("kpis", {})
outlier_rows = quality_payload.get("outlier_measures", [])
review_records = quality_payload.get("flagged_records", {})

# The backend owns the vocabulary and echoes which population it used,
# so the widget starts on the truth even on the very first render.
review_populations = quality_meta.get("review_populations", [])
active_review_population = quality_meta.get("review_population")

try:
    review_population_index = review_populations.index(
        active_review_population
    )
except ValueError:
    review_population_index = 0


with quality_tab:

    st.caption(
        "Team 6 treatment is Preserve source, flag anomalies, verify with "
        "the source owner before changing values. Extreme does not "
        "automatically mean error."
    )

    q1, q2, q3, q4 = st.columns(4)

    q1.metric(
        "Rows Needing Source Review",
        fmt_number(quality_kpis.get("rows_needing_source_review")),
    )

    q2.metric(
        "Data Quality Issue Rate",
        fmt_percent(dax.get("data_quality_issue_rate")),
    )

    q3.metric(
        "999 Vacancy Records",
        fmt_number(quality_kpis.get("vacancy_999_records")),
    )

    q4.metric(
        "RANDOM_JOB Records",
        fmt_number(quality_kpis.get("random_job_records")),
    )

    st.subheader("Team 6 Outlier Review")

    if outlier_rows:
        st.dataframe(
            outlier_rows,
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "Interpretation: these are review populations, not automatic "
        "deletions. Use median salary for broad summaries where extreme "
        "salaries distort the mean."
    )

    st.subheader("Inspect Flagged Records")

    st.selectbox(
        "Review population",
        options=review_populations,
        index=review_population_index,
        key="outlier_review_population",
    )

    st.caption(
        f"Showing up to {fmt_number(review_records.get('cap'))} records "
        f"from {fmt_number(review_records.get('total_matching'))} "
        "matching rows in the current filter context."
    )

    st.dataframe(
        review_records.get("data", []),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# REPOST ANALYSIS
# ============================================================
# Reposted/Non-Reposted row counts and the two aggregations come from
# the API. Repost Rate is deliberately NOT recomputed here:
# app_deploy.py computes it once and reuses it in the DAX expander and
# on this tab, so it is read from the already-fetched overview payload.

repost_payload = call_api(
    fetch_repost_analysis,
    repost_url,
    REQUEST_TIMEOUT,
)

repost_kpis = repost_payload.get("kpis", {})
status_counts = repost_payload.get("posting_status_counts", {})
status_salary = repost_payload.get("salary_by_posting_status", {})


with repost_tab:

    st.caption(
        "Repost analysis is descriptive. A repost flag identifies repeat "
        "posting behaviour; it does not by itself explain why the job was "
        "reposted."
    )

    r1, r2, r3 = st.columns(3)

    r1.metric(
        "Reposted Rows",
        fmt_number(repost_kpis.get("reposted_rows")),
    )

    r2.metric(
        "Repost Rate",
        fmt_percent(dax.get("repost_rate")),
    )

    r3.metric(
        "Non-Reposted Rows",
        fmt_number(repost_kpis.get("non_reposted_rows")),
    )

    if status_counts.get("available"):
        chart = (
            alt.Chart(
                alt.Data(
                    values=status_counts.get("data", []),
                )
            )
            .mark_bar()
            .encode(
                x=alt.X(
                    "Posting Status:N",
                    title=None,
                ),
                y=alt.Y(
                    "Jobs:Q",
                    title="Job Postings",
                ),
                tooltip=[
                    alt.Tooltip("Posting Status:N"),
                    alt.Tooltip("Jobs:Q", format=","),
                ],
            )
            .properties(height=350)
        )

        st.altair_chart(
            chart,
            use_container_width=True,
        )

    if status_salary.get("available"):
        st.dataframe(
            status_salary.get("data", []),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# DETAIL DRILLTHROUGH
# ============================================================
# Row-level lookups. The two selectboxes below are rendered in their
# reference positions but read from session state first, because their
# values decide what the API is asked for.

rows_requested = st.session_state.get(
    "drillthrough_rows_to_show",
    ROWS_TO_SHOW_DEFAULT,
)

jobs_url = build_api_url(
    JOBS_URL,
    selections,
    [("limit", rows_requested), ("offset", 0)],
)

job_ids_url = build_api_url(
    JOB_IDS_URL,
    selections,
    [("limit", JOB_ID_LIMIT)],
)

jobs_payload = call_api(fetch_jobs, jobs_url, REQUEST_TIMEOUT)
job_ids_payload = call_api(fetch_job_ids, job_ids_url, REQUEST_TIMEOUT)

jobs_meta = jobs_payload.get("meta", {})
job_ids_meta = job_ids_payload.get("meta", {})
job_columns = jobs_payload.get("columns", [])
job_rows = jobs_payload.get("rows", [])
drill_job_ids = job_ids_payload.get("job_ids", [])
drill_available = job_ids_meta.get("available", False)

# The job id is read before the selectbox renders; the reference's
# selector has no explicit index, so it starts on the first option.
selected_job_id = st.session_state.get("drillthrough_job_id")

job_detail_payload = {"meta": {"found": False}, "record": None, "metrics": {}}
job_categories_payload = {"meta": {}, "columns": [], "rows": []}
job_skills_payload = {"meta": {}, "columns": [], "rows": []}

if selected_job_id:
    # Quote in case an id contains a slash or other path character.
    quoted_job_id = quote(str(selected_job_id), safe="")

    detail_url = build_api_url(
        f"{JOBS_URL}/{quoted_job_id}",
        selections,
    )

    job_detail_payload = call_api(
        fetch_job_detail,
        detail_url,
        REQUEST_TIMEOUT,
    )

    # Bridge lookups are matched on the job id alone, so no filter
    # parameters are sent: the reference shows a job's full multi-label
    # history regardless of the active filter.
    job_categories_payload = call_api(
        fetch_job_bridge,
        f"{JOBS_URL}/{quoted_job_id}/categories",
        REQUEST_TIMEOUT,
    )

    job_skills_payload = call_api(
        fetch_job_bridge,
        f"{JOBS_URL}/{quoted_job_id}/skills",
        REQUEST_TIMEOUT,
    )

job_detail_meta = job_detail_payload.get("meta", {})
job_metrics = job_detail_payload.get("metrics", {})
job_record = job_detail_payload.get("record")


with records_tab:

    st.subheader("Filtered Job Records")

    st.selectbox(
        "Rows to display",
        options=ROWS_TO_SHOW_OPTIONS,
        index=ROWS_TO_SHOW_OPTIONS.index(ROWS_TO_SHOW_DEFAULT),
        key="drillthrough_rows_to_show",
    )

    st.dataframe(
        job_rows,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Job Drillthrough")

    if drill_available:

        st.selectbox(
            "Select Job ID",
            options=drill_job_ids,
            key="drillthrough_job_id",
        )

        if job_detail_meta.get("found") and job_record:

            d1, d2, d3, d4 = st.columns(4)

            d1.metric(
                "Salary Midpoint",
                fmt_currency(job_metrics.get("salary_midpoint")),
            )

            d2.metric(
                "Vacancies",
                fmt_number(job_metrics.get("number_of_vacancies")),
            )

            d3.metric(
                "Applications / Vacancy",
                fmt_decimal(
                    job_metrics.get("applications_per_vacancy"),
                    places=2,
                ),
            )

            d4.metric(
                "Opportunity Score",
                fmt_decimal(
                    job_metrics.get("opportunity_score"),
                    places=1,
                ),
            )

            # The reference renders every field as text, with missing
            # values as null, so the JSON block is stringified here too.
            st.json(
                {
                    key: (
                        None
                        if value is None
                        else str(value)
                    )
                    for key, value in job_record.items()
                }
            )

            drill_left, drill_right = st.columns(2)

            with drill_left:
                st.write("**All Job Functions from bridge**")
                st.dataframe(
                    job_categories_payload.get("rows", []),
                    use_container_width=True,
                    hide_index=True,
                )

            with drill_right:
                st.write("**All Skills from bridge**")
                st.dataframe(
                    job_skills_payload.get("rows", []),
                    use_container_width=True,
                    hide_index=True,
                )


# ============================================================
# TECHNICAL INFO
# ============================================================

with st.expander("Technical details"):

    st.write(
        {
            "api_base_url": API_BASE_URL,
            "endpoint": meta.get("endpoint"),
            "request_url": overview_url,
            "charts_request_url": charts_url,
            "salary_request_url": salary_url,
            "opportunity_request_url": opportunity_url,
            "demand_request_url": demand_url,
            "bridge_request_url": bridge_url,
            "quality_request_url": quality_url,
            "repost_request_url": repost_url,
            "jobs_request_url": jobs_url,
            "job_ids_request_url": job_ids_url,
            "chart_rows_returned": {
                key: len(value.get("data", []))
                for key, value in charts.items()
            },
            "salary_rows_returned": {
                "salary_band_counts": len(
                    salary_band_counts.get("data", [])
                ),
                "average_salary_by_job_function": len(
                    salary_by_function.get("data", [])
                ),
                "summary_measures": 5,
            },
            "opportunity_rows_returned": {
                "opportunity_band_counts": len(
                    opportunity_bands.get("data", [])
                ),
                "top_job_functions": len(
                    opportunity_ranking.get("data", [])
                ),
                "ranking_min_jobs": opportunity_ranking.get("min_jobs"),
                "ranking_fallback_applied": (
                    opportunity_ranking.get("fallback_applied")
                ),
            },
            "demand_rows_returned": {
                "seniority_counts": len(
                    seniority_counts.get("data", [])
                ),
                "average_salary_by_seniority": len(
                    seniority_salary.get("data", [])
                ),
                "scatter_rows": len(scatter.get("data", [])),
                "scatter_sampled": scatter.get("sampled"),
                "scatter_sample_limit": (
                    demand_payload.get("meta", {}).get(
                        "scatter_sample_limit"
                    )
                ),
            },
            "bridge_rows_returned": {
                "top_categories": len(top_categories.get("data", [])),
                "top_skills": len(top_skills.get("data", [])),
                "count_metric": bridge_payload.get("meta", {}).get(
                    "count_metric"
                ),
            },
            "quality_rows_returned": {
                "review_population": quality_meta.get(
                    "review_population"
                ),
                "outlier_measures": len(outlier_rows),
                "review_rows_shown": review_records.get("rows_shown"),
                "review_cap": review_records.get("cap"),
                "review_total_matching": review_records.get(
                    "total_matching"
                ),
                "issue_rate_source": quality_meta.get("issue_rate_source"),
            },
            "repost_rows_returned": {
                "reposted_rows": repost_kpis.get("reposted_rows"),
                "non_reposted_rows": repost_kpis.get("non_reposted_rows"),
                "posting_status_counts": len(status_counts.get("data", [])),
                "salary_by_posting_status": len(
                    status_salary.get("data", [])
                ),
                "count_unit": repost_payload.get("meta", {}).get(
                    "count_unit"
                ),
                "repost_rate_source": repost_payload.get("meta", {}).get(
                    "repost_rate_source"
                ),
            },
            "drillthrough_rows_returned": {
                "records_returned": jobs_meta.get("returned"),
                "records_limit": jobs_meta.get("limit"),
                "records_offset": jobs_meta.get("offset"),
                "records_has_more": jobs_meta.get("has_more"),
                "record_columns": len(job_columns),
                "job_ids_returned": job_ids_meta.get("returned"),
                "job_ids_unique_in_window": job_ids_meta.get(
                    "unique_in_window"
                ),
                "job_ids_duplicates_kept": job_ids_meta.get(
                    "duplicates_kept"
                ),
                "selected_job_id": selected_job_id,
                "selected_job_found": job_detail_meta.get("found"),
                "selected_job_matching_rows": job_detail_meta.get(
                    "matching_rows"
                ),
                "bridge_categories_returned": job_categories_payload.get(
                    "meta",
                    {},
                ).get("returned"),
                "bridge_skills_returned": job_skills_payload.get(
                    "meta",
                    {},
                ).get("returned"),
            },
            "source": meta.get("source"),
            "data_file": meta.get("data_file"),
            "source_type": meta.get("source_type"),
            "rows": meta.get("rows_total"),
            "loaded_columns": meta.get("columns_loaded"),
            "filtered_rows": meta.get("rows_filtered"),
            "filters_applied": meta.get("filters_applied"),
            "active_filters": meta.get("active_filters"),
            "v3_expected_rows": meta.get("v3_expected_rows"),
            "category_bridge_rows": meta.get("category_bridge_rows"),
            "skill_bridge_rows": meta.get("skill_bridge_rows"),
            "backend_load_seconds": meta.get("load_seconds"),
            "dax_equivalent_measures": [
                "Average Application Rate",
                "Average Applications per Vacancy",
                "Average Minimum Experience",
                "Average Salary Midpoint",
                "Average Views per Vacancy",
                "Data Quality Issue Rate",
                "Distinct Categories",
                "Distinct Skills",
                "High Opportunity Jobs",
                "Median Salary Midpoint",
                "Overall Applications per Vacancy",
                "Repost Rate",
                "Total Applications",
                "Total Job Postings",
                "Total Vacancies",
                "Unique Job Postings",
                "Skill Job Postings",
                "Category Job Postings",
            ],
        }
    )

    st.caption(
        "Compare these values against the identical filter set and KPI "
        "cards in app_deploy.py."
    )


if st.sidebar.button("Check API health"):
    try:
        st.sidebar.json(fetch_health(HEALTH_URL, REQUEST_TIMEOUT))
    except requests.exceptions.RequestException as error:
        st.sidebar.error(f"{type(error).__name__}: {error}")