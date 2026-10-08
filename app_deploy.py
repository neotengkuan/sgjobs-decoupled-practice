from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="SGJobs Interactive Dashboard",
    page_icon="💼",
    layout="wide",
)


# ============================================================
# DEPLOYMENT DATA SOURCES
# ============================================================
# All cloud paths are relative to this app file.
# Keep the validated local app.py unchanged.

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

PARQUET_FILE = DATA_DIR / "sgjob_v3_clean_features.parquet"
CSV_FILE = DATA_DIR / "sgjob_v3_clean_features.csv"
CSV_FALLBACK = CSV_FILE

# Bridge Parquet is preferred for cloud deployment because it is
# smaller/faster than CSV. CSV remains a fallback for compatibility.
CATEGORY_BRIDGE_PARQUET = DATA_DIR / "sgjob_v3_category_bridge.parquet"
CATEGORY_BRIDGE_FILE = DATA_DIR / "sgjob_v3_category_bridge.csv"

SKILL_BRIDGE_PARQUET = DATA_DIR / "sgjob_v3_skill_bridge.parquet"
SKILL_BRIDGE_FILE = DATA_DIR / "sgjob_v3_skill_bridge.csv"

DEPLOYMENT_CACHE_VERSION = "validated_v3_deploy_1"


# Only load columns actually needed by the dashboard.
WANTED_COLUMNS = [
    # Keys / display
    "metadata_job_post_id",
    "title_clean",
    "employment_types",
    "category_primary",

    # Salary / experience / vacancies
    "salary_minimum",
    "salary_maximum",
    "salary_midpoint",
    "salary_band",
    "minimum_years_experience",
    "experience_band",
    "number_of_vacancies",
    "vacancy_band",

    # Seniority
    "position_level_clean",
    "seniority_group",

    # Demand / competition
    "metadata_total_number_job_application",
    "metadata_total_number_of_view",
    "applications_per_vacancy",
    "views_per_vacancy",
    "application_rate",

    # Opportunity
    "opportunity_score",
    "opportunity_band",

    # Time / repost
    "posting_year",
    "month_year",
    "month_year_sort",
    "metadata_new_posting_date",
    "metadata_expiry_date",
    "posting_duration_days",
    "is_reposted",

    # Skills convenience field
    "skill_tags",
    "skill_count",

    # Team 6 review / data-quality fields
    "job_id_format",
    "random_job_review_flag",
    "salary_high_review_flag",
    "experience_high_review_flag",
    "vacancy_high_review_flag",
    "vacancy_999_review_flag",
    "needs_source_review",
    "duplicate_job_id",
    "has_data_quality_issue",
]


# ============================================================
# HELPERS
# ============================================================

def first_existing_path():
    for path in [PARQUET_FILE, CSV_FILE, CSV_FALLBACK]:
        if path.exists():
            return path
    return None


def available_parquet_columns(path):
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).schema.names


@st.cache_data(show_spinner="Loading category bridge...")
def load_category_bridge(cache_version):
    """Load only the two columns needed for category analysis."""
    required = ["job_post_id", "category_name"]

    if CATEGORY_BRIDGE_PARQUET.exists():
        return pd.read_parquet(
            CATEGORY_BRIDGE_PARQUET,
            columns=required,
        )

    if not CATEGORY_BRIDGE_FILE.exists():
        return pd.DataFrame(columns=required)

    header = pd.read_csv(CATEGORY_BRIDGE_FILE, nrows=0)
    if not all(col in header.columns for col in required):
        return pd.DataFrame(columns=required)

    return pd.read_csv(
        CATEGORY_BRIDGE_FILE,
        usecols=required,
        low_memory=True,
    )


@st.cache_data(show_spinner="Loading skill bridge...")
def load_skill_bridge(cache_version):
    """Load only the two columns needed for skill analysis."""
    required = ["job_post_id", "skill_name"]

    if SKILL_BRIDGE_PARQUET.exists():
        return pd.read_parquet(
            SKILL_BRIDGE_PARQUET,
            columns=required,
        )

    if not SKILL_BRIDGE_FILE.exists():
        return pd.DataFrame(columns=required)

    header = pd.read_csv(SKILL_BRIDGE_FILE, nrows=0)
    if not all(col in header.columns for col in required):
        return pd.DataFrame(columns=required)

    return pd.read_csv(
        SKILL_BRIDGE_FILE,
        usecols=required,
        low_memory=True,
    )


@st.cache_data(show_spinner="Loading optimized SGJobs dataset...")
def load_dashboard_data(path_string, wanted_columns, cache_version):
    """
    Load only dashboard columns.
    Parquet is preferred because it is faster and more memory-efficient.
    """
    path = Path(path_string)

    if path.suffix.lower() == ".parquet":
        available = set(available_parquet_columns(path))
        usecols = [c for c in wanted_columns if c in available]
        data = pd.read_parquet(path, columns=usecols)

    else:
        header = pd.read_csv(path, nrows=0)
        available = set(header.columns)
        usecols = [c for c in wanted_columns if c in available]

        data = pd.read_csv(
            path,
            usecols=usecols,
            low_memory=True,
        )

    # ============================================================
    # LIGHTWEIGHT DATA PREPARATION
    # ============================================================
    # These steps run inside the cached loader so that only the
    # optimised, memory-lean DataFrame is stored in the cache and
    # copied on each rerun.

    # Numeric columns.
    for col in [
        "salary_midpoint",
        "number_of_vacancies",
        "opportunity_score",
        "posting_year",
        "month_year_sort",
    ]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    # Date column only if needed.
    if "metadata_new_posting_date" in data.columns:
        data["metadata_new_posting_date"] = pd.to_datetime(
            data["metadata_new_posting_date"],
            errors="coerce",
        )

    # Derive posting_year only if it is missing.
    if (
        "posting_year" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["posting_year"] = data["metadata_new_posting_date"].dt.year

    # Derive month_year only if it is missing.
    if (
        "month_year" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["month_year"] = (
            data["metadata_new_posting_date"]
            .dt.to_period("M")
            .astype("string")
        )

    # Derive month_year_sort only if it is missing.
    if (
        "month_year_sort" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["month_year_sort"] = (
            data["metadata_new_posting_date"].dt.year * 100
            + data["metadata_new_posting_date"].dt.month
        )

    # Use categorical dtype for repeated text fields to save RAM.
    for col in [
        "employment_types",
        "category_primary",
        "salary_band",
        "opportunity_band",
        "month_year",
    ]:
        if col in data.columns:
            data[col] = data[col].astype("category")

    return data


def fmt_number(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def fmt_currency(value):
    if pd.isna(value):
        return "N/A"
    return f"S${value:,.0f}"


def fmt_percent(value):
    if pd.isna(value):
        return "N/A"
    return f"{value * 100:.1f}%"


def reset_filters():
    for key in [
        "employment_filter",
        "job_function_filter",
        "category_bridge_filter",
        "skill_bridge_filter",
        "salary_band_filter",
        "seniority_filter",
        "experience_band_filter",
        "vacancy_band_filter",
        "opportunity_band_filter",
        "posting_year_filter",
    ]:
        st.session_state[key] = []


# ============================================================
# FIND AND LOAD DATA
# ============================================================

DATA_FILE = first_existing_path()

if DATA_FILE is None:
    st.error(
        "No deployment data file was found.\n\n"
        "Expected inside the repository data/ folder:\n"
        "- data/sgjob_v3_clean_features.parquet\n"
        "or\n"
        "- data/sgjob_v3_clean_features.csv"
    )
    st.stop()


df = load_dashboard_data(
    str(DATA_FILE),
    tuple(WANTED_COLUMNS),
    DEPLOYMENT_CACHE_VERSION,
)


# Load the two bridge tables separately.
# IMPORTANT:
# category_primary remains the main-table field used by the existing
# Job Function slicer and existing Job Function visuals.
category_bridge = load_category_bridge(DEPLOYMENT_CACHE_VERSION)
skill_bridge = load_skill_bridge(DEPLOYMENT_CACHE_VERSION)

# Repeated labels are stored as categories to reduce memory.
if (
    not category_bridge.empty
    and "category_name" in category_bridge.columns
):
    category_bridge["category_name"] = (
        category_bridge["category_name"]
        .astype("category")
    )

if (
    not skill_bridge.empty
    and "skill_name" in skill_bridge.columns
):
    skill_bridge["skill_name"] = (
        skill_bridge["skill_name"]
        .astype("category")
    )


# ============================================================
# PAGE HEADER
# ============================================================

st.title("💼 SGJobs Interactive Dashboard")
st.caption(
    "V3 baseline: 1,044,597 validated logical records | "
    "Expanded Power BI-equivalent analysis + multi-label bridges"
)
st.caption("Deployment build: repository-relative data paths; validated local app remains separate.")

source_label = (
    "Parquet"
    if DATA_FILE.suffix.lower() == ".parquet"
    else "CSV"
)

st.caption(
    f"Optimized source: {DATA_FILE.name} ({source_label})  |  "
    f"Rows loaded: {len(df):,}  |  "
    f"Columns loaded: {len(df.columns):,}"
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("Filters")


employment_selected = []

if "employment_types" in df.columns:
    employment_options = sorted(
        df["employment_types"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    employment_selected = st.sidebar.multiselect(
        "Employment Type",
        options=employment_options,
        key="employment_filter",
    )


job_function_selected = []

if "category_primary" in df.columns:
    job_function_options = sorted(
        df["category_primary"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    job_function_selected = st.sidebar.multiselect(
        "Job Function",
        options=job_function_options,
        key="job_function_filter",
    )


# Official multi-label Job Function slicer from Team 6's category bridge.
category_bridge_selected = []

if (
    not category_bridge.empty
    and "category_name" in category_bridge.columns
):
    category_bridge_options = sorted(
        category_bridge["category_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    category_bridge_selected = st.sidebar.multiselect(
        "Job Function (Bridge)",
        options=category_bridge_options,
        key="category_bridge_filter",
        help=(
            "Recommended for official Job Function analysis. "
            "A job can belong to more than one Job Function."
        ),
    )


skill_bridge_selected = []

if (
    not skill_bridge.empty
    and "skill_name" in skill_bridge.columns
):
    skill_bridge_options = sorted(
        skill_bridge["skill_name"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    skill_bridge_selected = st.sidebar.multiselect(
        "Skill",
        options=skill_bridge_options,
        key="skill_bridge_filter",
    )


seniority_selected = []

if "seniority_group" in df.columns:
    seniority_options = sorted(
        df["seniority_group"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    seniority_selected = st.sidebar.multiselect(
        "Seniority",
        options=seniority_options,
        key="seniority_filter",
    )


experience_band_selected = []

if "experience_band" in df.columns:
    experience_options = (
        df["experience_band"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    experience_band_selected = st.sidebar.multiselect(
        "Experience Band",
        options=experience_options,
        key="experience_band_filter",
    )


vacancy_band_selected = []

if "vacancy_band" in df.columns:
    vacancy_options = (
        df["vacancy_band"]
        .dropna()
        .astype(str)
        .drop_duplicates()
        .tolist()
    )

    vacancy_band_selected = st.sidebar.multiselect(
        "Vacancy Band",
        options=vacancy_options,
        key="vacancy_band_filter",
    )


salary_band_selected = []

if "salary_band" in df.columns:
    preferred_order = [
        "< 3K",
        "3K–5K",
        "5K–7K",
        "7K–10K",
        "10K+",
        "Unknown",
    ]

    actual = set(
        df["salary_band"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    salary_options = [
        x for x in preferred_order
        if x in actual
    ]

    salary_options += sorted(
        actual - set(salary_options)
    )

    salary_band_selected = st.sidebar.multiselect(
        "Salary Band",
        options=salary_options,
        key="salary_band_filter",
    )


opportunity_band_selected = []

if "opportunity_band" in df.columns:
    preferred_order = [
        "Low",
        "Moderate",
        "Good",
        "High",
    ]

    actual = set(
        df["opportunity_band"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    opportunity_options = [
        x for x in preferred_order
        if x in actual
    ]

    opportunity_options += sorted(
        actual - set(opportunity_options)
    )

    opportunity_band_selected = st.sidebar.multiselect(
        "Opportunity Band",
        options=opportunity_options,
        key="opportunity_band_filter",
    )


posting_year_selected = []

if "posting_year" in df.columns:
    posting_year_options = sorted(
        df["posting_year"]
        .dropna()
        .astype(int)
        .unique()
        .tolist()
    )

    posting_year_selected = st.sidebar.multiselect(
        "Posting Year",
        options=posting_year_options,
        key="posting_year_filter",
    )


st.sidebar.button(
    "Reset Filters",
    on_click=reset_filters,
)


# ============================================================
# FAST FILTER MASK
# ============================================================

mask = pd.Series(True, index=df.index)


if employment_selected:
    mask &= df["employment_types"].isin(
        employment_selected
    )


if job_function_selected:
    mask &= df["category_primary"].isin(
        job_function_selected
    )


if category_bridge_selected:
    matching_category_jobs = (
        category_bridge.loc[
            category_bridge["category_name"]
            .astype(str)
            .isin(category_bridge_selected),
            "job_post_id",
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    mask &= (
        df["metadata_job_post_id"]
        .astype(str)
        .isin(matching_category_jobs)
    )


if skill_bridge_selected:
    matching_skill_jobs = (
        skill_bridge.loc[
            skill_bridge["skill_name"]
            .astype(str)
            .isin(skill_bridge_selected),
            "job_post_id",
        ]
        .dropna()
        .astype(str)
        .unique()
    )

    mask &= (
        df["metadata_job_post_id"]
        .astype(str)
        .isin(matching_skill_jobs)
    )


if seniority_selected:
    mask &= df["seniority_group"].isin(
        seniority_selected
    )


if experience_band_selected:
    mask &= df["experience_band"].isin(
        experience_band_selected
    )


if vacancy_band_selected:
    mask &= df["vacancy_band"].isin(
        vacancy_band_selected
    )


if salary_band_selected:
    mask &= df["salary_band"].isin(
        salary_band_selected
    )


if opportunity_band_selected:
    mask &= df["opportunity_band"].isin(
        opportunity_band_selected
    )


if posting_year_selected:
    mask &= df["posting_year"].isin(
        posting_year_selected
    )


filtered = df.loc[mask]


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_jobs = len(filtered)

average_salary = (
    filtered["salary_midpoint"].mean()
    if "salary_midpoint" in filtered.columns
    else float("nan")
)

median_salary = (
    filtered["salary_midpoint"].median()
    if "salary_midpoint" in filtered.columns
    else float("nan")
)

total_vacancies = (
    filtered["number_of_vacancies"].sum()
    if "number_of_vacancies" in filtered.columns
    else float("nan")
)

avg_opportunity = (
    filtered["opportunity_score"].mean()
    if "opportunity_score" in filtered.columns
    else float("nan")
)


# ============================================================
# POWER BI / DAX-EQUIVALENT MEASURES
# ============================================================

unique_job_postings = (
    filtered["metadata_job_post_id"].nunique()
    if "metadata_job_post_id" in filtered.columns
    else len(filtered)
)

total_applications = (
    filtered["metadata_total_number_job_application"].sum()
    if "metadata_total_number_job_application" in filtered.columns
    else float("nan")
)

average_application_rate = (
    filtered["application_rate"].mean()
    if "application_rate" in filtered.columns
    else float("nan")
)

average_applications_per_vacancy = (
    filtered["applications_per_vacancy"].mean()
    if "applications_per_vacancy" in filtered.columns
    else float("nan")
)

average_views_per_vacancy = (
    filtered["views_per_vacancy"].mean()
    if "views_per_vacancy" in filtered.columns
    else float("nan")
)

average_minimum_experience = (
    filtered["minimum_years_experience"].mean()
    if "minimum_years_experience" in filtered.columns
    else float("nan")
)

overall_applications_per_vacancy = (
    total_applications / total_vacancies
    if (
        pd.notna(total_applications)
        and pd.notna(total_vacancies)
        and total_vacancies != 0
    )
    else float("nan")
)

high_opportunity_jobs = (
    filtered.loc[
        filtered["opportunity_band"].astype(str).eq("High"),
        "metadata_job_post_id",
    ].nunique()
    if (
        "opportunity_band" in filtered.columns
        and "metadata_job_post_id" in filtered.columns
    )
    else 0
)

data_quality_issue_rate = (
    filtered["has_data_quality_issue"]
    .fillna(False)
    .astype(bool)
    .mean()
    if "has_data_quality_issue" in filtered.columns
    else float("nan")
)

repost_rate = (
    filtered["is_reposted"]
    .fillna(False)
    .astype(bool)
    .mean()
    if "is_reposted" in filtered.columns
    else float("nan")
)


# Bridge-table measures.
distinct_categories = (
    category_bridge["category_name"].nunique()
    if "category_name" in category_bridge.columns
    else 0
)

distinct_skills = (
    skill_bridge["skill_name"].nunique()
    if "skill_name" in skill_bridge.columns
    else 0
)

category_job_postings = (
    category_bridge["job_post_id"].nunique()
    if "job_post_id" in category_bridge.columns
    else 0
)

skill_job_postings = (
    skill_bridge["job_post_id"].nunique()
    if "job_post_id" in skill_bridge.columns
    else 0
)


# ============================================================
# KPI CARDS
# ============================================================

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric(
    "Total Jobs",
    fmt_number(total_jobs),
)

k2.metric(
    "Average Salary",
    fmt_currency(average_salary),
)

k3.metric(
    "Median Salary",
    fmt_currency(median_salary),
)

k4.metric(
    "Total Vacancies",
    fmt_number(total_vacancies),
)

k5.metric(
    "Avg Opportunity Score",
    f"{avg_opportunity:.1f}"
    if pd.notna(avg_opportunity)
    else "N/A",
)

st.caption(
    f"Showing {len(filtered):,} of {len(df):,} job records"
)


bridge_k1, bridge_k2, bridge_k3, bridge_k4 = st.columns(4)

bridge_k1.metric(
    "Distinct Categories",
    fmt_number(distinct_categories),
)

bridge_k2.metric(
    "Category Job Postings",
    fmt_number(category_job_postings),
)

bridge_k3.metric(
    "Distinct Skills",
    fmt_number(distinct_skills),
)

bridge_k4.metric(
    "Skill Job Postings",
    fmt_number(skill_job_postings),
)


with st.expander("Power BI / DAX-equivalent measures", expanded=False):
    m1, m2, m3, m4 = st.columns(4)

    m1.metric(
        "Unique Job Postings",
        fmt_number(unique_job_postings),
    )

    m2.metric(
        "Total Applications",
        fmt_number(total_applications),
    )

    m3.metric(
        "Overall Applications / Vacancy",
        f"{overall_applications_per_vacancy:.2f}"
        if pd.notna(overall_applications_per_vacancy)
        else "N/A",
    )

    m4.metric(
        "High Opportunity Jobs",
        fmt_number(high_opportunity_jobs),
    )

    m5, m6, m7, m8 = st.columns(4)

    m5.metric(
        "Average Application Rate",
        fmt_percent(average_application_rate),
    )

    m6.metric(
        "Average Applications / Vacancy",
        f"{average_applications_per_vacancy:.2f}"
        if pd.notna(average_applications_per_vacancy)
        else "N/A",
    )

    m7.metric(
        "Average Views / Vacancy",
        f"{average_views_per_vacancy:.2f}"
        if pd.notna(average_views_per_vacancy)
        else "N/A",
    )

    m8.metric(
        "Average Minimum Experience",
        f"{average_minimum_experience:.1f} years"
        if pd.notna(average_minimum_experience)
        else "N/A",
    )

    m9, m10 = st.columns(2)

    m9.metric(
        "Data Quality Issue Rate",
        fmt_percent(data_quality_issue_rate),
    )

    m10.metric(
        "Repost Rate",
        fmt_percent(repost_rate),
    )


# ============================================================
# TABS
# ============================================================

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

with overview_tab:

    col_left, col_right = st.columns(2)

    # Jobs by Employment Type
    with col_left:
        st.subheader("Jobs by Employment Type")

        if (
            "employment_types" in filtered.columns
            and not filtered.empty
        ):
            summary = (
                filtered["employment_types"]
                .value_counts(dropna=True)
                .rename_axis("Employment Type")
                .reset_index(name="Jobs")
            )

            chart = (
                alt.Chart(summary)
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

        if (
            "category_primary" in filtered.columns
            and not filtered.empty
        ):
            summary = (
                filtered["category_primary"]
                .value_counts(dropna=True)
                .head(15)
                .rename_axis("Job Function")
                .reset_index(name="Jobs")
            )

            chart = (
                alt.Chart(summary)
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

        if (
            "month_year" in filtered.columns
            and not filtered.empty
        ):

            if "month_year_sort" in filtered.columns:
                summary = (
                    filtered[
                        ["month_year", "month_year_sort"]
                    ]
                    .dropna()
                    .groupby(
                        ["month_year", "month_year_sort"],
                        observed=True,
                        as_index=False,
                    )
                    .size()
                    .rename(columns={"size": "Jobs"})
                    .sort_values("month_year_sort")
                )

            else:
                summary = (
                    filtered["month_year"]
                    .value_counts(sort=False)
                    .rename_axis("month_year")
                    .reset_index(name="Jobs")
                )

            chart = (
                alt.Chart(summary)
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

        if (
            "category_primary" in filtered.columns
            and "number_of_vacancies" in filtered.columns
            and not filtered.empty
        ):

            summary = (
                filtered[
                    [
                        "category_primary",
                        "number_of_vacancies",
                    ]
                ]
                .dropna()
                .groupby(
                    "category_primary",
                    observed=True,
                    as_index=False,
                )["number_of_vacancies"]
                .sum()
                .sort_values(
                    "number_of_vacancies",
                    ascending=False,
                )
                .head(10)
                .rename(
                    columns={
                        "category_primary": "Job Function",
                        "number_of_vacancies": "Vacancies",
                    }
                )
            )

            chart = (
                alt.Chart(summary)
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

with salary_tab:

    salary_left, salary_right = st.columns(2)


    with salary_left:
        st.subheader("Jobs by Salary Band")

        if (
            "salary_band" in filtered.columns
            and not filtered.empty
        ):
            summary = (
                filtered["salary_band"]
                .value_counts(dropna=True)
                .rename_axis("Salary Band")
                .reset_index(name="Jobs")
            )

            chart = (
                alt.Chart(summary)
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

        if (
            "category_primary" in filtered.columns
            and "salary_midpoint" in filtered.columns
            and not filtered.empty
        ):

            top_functions = (
                filtered["category_primary"]
                .value_counts(dropna=True)
                .head(15)
                .index
            )

            summary = (
                filtered[
                    filtered["category_primary"].isin(
                        top_functions
                    )
                ]
                .groupby(
                    "category_primary",
                    observed=True,
                    as_index=False,
                )["salary_midpoint"]
                .mean()
                .dropna()
                .sort_values(
                    "salary_midpoint",
                    ascending=False,
                )
                .rename(
                    columns={
                        "category_primary": "Job Function",
                        "salary_midpoint": "Average Salary",
                    }
                )
            )

            chart = (
                alt.Chart(summary)
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

    if (
        "salary_midpoint" in filtered.columns
        and not filtered.empty
    ):

        salary_series = filtered["salary_midpoint"]

        summary_table = pd.DataFrame(
            {
                "Measure": [
                    "Jobs with salary data",
                    "Average salary",
                    "Median salary",
                    "Minimum salary midpoint",
                    "Maximum salary midpoint",
                ],
                "Value": [
                    f"{salary_series.notna().sum():,}",
                    fmt_currency(salary_series.mean()),
                    fmt_currency(salary_series.median()),
                    fmt_currency(salary_series.min()),
                    fmt_currency(salary_series.max()),
                ],
            }
        )

        st.dataframe(
            summary_table,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# OPPORTUNITY ANALYSIS
# ============================================================

with opportunity_tab:

    st.caption(
        "Opportunity Score is exploratory/indicative, not a validated predictive model."
    )

    opp_left, opp_right = st.columns(2)


    with opp_left:
        st.subheader("Jobs by Opportunity Band")

        if (
            "opportunity_band" in filtered.columns
            and not filtered.empty
        ):

            summary = (
                filtered["opportunity_band"]
                .value_counts(dropna=True)
                .rename_axis("Opportunity Band")
                .reset_index(name="Jobs")
            )

            chart = (
                alt.Chart(summary)
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

        if (
            "category_primary" in filtered.columns
            and "opportunity_score" in filtered.columns
            and not filtered.empty
        ):

            summary = (
                filtered[
                    [
                        "category_primary",
                        "opportunity_score",
                    ]
                ]
                .dropna()
                .groupby(
                    "category_primary",
                    observed=True,
                )
                .agg(
                    average_opportunity=(
                        "opportunity_score",
                        "mean",
                    ),
                    jobs=(
                        "opportunity_score",
                        "size",
                    ),
                )
                .reset_index()
            )

            # Avoid tiny categories dominating the ranking.
            # Keep the original 100-job rule for large selections, but
            # reduce it for small filtered samples so the chart does not
            # disappear when only a few hundred records remain.
            if len(filtered) >= 5_000:
                min_jobs = 100
            else:
                min_jobs = max(5, int(len(filtered) * 0.02))

            ranked = summary[summary["jobs"] >= min_jobs].copy()

            # If no category passes the adaptive threshold, show the
            # available categories rather than rendering a blank panel.
            if ranked.empty and not summary.empty:
                ranked = summary.copy()
                st.caption(
                    "No job function met the minimum sample-size rule for "
                    "this filter selection, so all available functions are shown."
                )
            else:
                st.caption(
                    f"Ranking uses job functions with at least {min_jobs:,} matching jobs."
                )

            summary = (
                ranked
                .sort_values(
                    ["average_opportunity", "jobs"],
                    ascending=[False, False],
                )
                .head(15)
                .rename(
                    columns={
                        "category_primary": "Job Function",
                        "average_opportunity": "Average Opportunity Score",
                        "jobs": "Jobs",
                    }
                )
            )

            chart = (
                alt.Chart(summary)
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

with demand_tab:

    st.caption(
        "Demand measures mirror the Power BI business view. "
        "The scatter plot is descriptive; it does not imply causation."
    )

    demand_left, demand_right = st.columns(2)

    with demand_left:
        st.subheader("Jobs by Seniority")

        if (
            "seniority_group" in filtered.columns
            and not filtered.empty
        ):
            seniority_summary = (
                filtered["seniority_group"]
                .value_counts(dropna=True)
                .rename_axis("Seniority")
                .reset_index(name="Jobs")
            )

            seniority_chart = (
                alt.Chart(seniority_summary)
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
                seniority_chart,
                use_container_width=True,
            )

    with demand_right:
        st.subheader("Average Salary by Seniority")

        if (
            "seniority_group" in filtered.columns
            and "salary_midpoint" in filtered.columns
            and not filtered.empty
        ):
            seniority_salary = (
                filtered[
                    [
                        "seniority_group",
                        "salary_midpoint",
                    ]
                ]
                .dropna()
                .groupby(
                    "seniority_group",
                    observed=True,
                )
                .agg(
                    average_salary=("salary_midpoint", "mean"),
                    median_salary=("salary_midpoint", "median"),
                    jobs=("salary_midpoint", "size"),
                )
                .reset_index()
                .rename(
                    columns={
                        "seniority_group": "Seniority",
                        "average_salary": "Average Salary",
                        "median_salary": "Median Salary",
                        "jobs": "Jobs",
                    }
                )
            )

            chart = (
                alt.Chart(seniority_salary)
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

    scatter_columns = [
        "metadata_job_post_id",
        "category_primary",
        "seniority_group",
        "salary_midpoint",
        "number_of_vacancies",
        "applications_per_vacancy",
        "views_per_vacancy",
        "application_rate",
        "opportunity_score",
    ]

    if all(
        col in filtered.columns
        for col in [
            "salary_midpoint",
            "applications_per_vacancy",
            "number_of_vacancies",
        ]
    ):
        scatter_data = (
            filtered[
                [
                    c
                    for c in scatter_columns
                    if c in filtered.columns
                ]
            ]
            .replace(
                [float("inf"), float("-inf")],
                pd.NA,
            )
            .dropna(
                subset=[
                    "salary_midpoint",
                    "applications_per_vacancy",
                    "number_of_vacancies",
                ]
            )
        )

        # Keep browser rendering responsive without changing KPI calculations.
        if len(scatter_data) > 25_000:
            scatter_data = scatter_data.sample(
                25_000,
                random_state=42,
            )
            st.caption(
                "Scatter plot displays a reproducible 25,000-row sample "
                "for browser performance; dashboard measures still use all filtered rows."
            )

        tooltip_fields = []

        if "metadata_job_post_id" in scatter_data.columns:
            tooltip_fields.append(
                alt.Tooltip(
                    "metadata_job_post_id:N",
                    title="Job ID",
                )
            )

        if "category_primary" in scatter_data.columns:
            tooltip_fields.append(
                alt.Tooltip(
                    "category_primary:N",
                    title="Job Function (compat.)",
                )
            )

        if "seniority_group" in scatter_data.columns:
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

        if "views_per_vacancy" in scatter_data.columns:
            tooltip_fields.append(
                alt.Tooltip(
                    "views_per_vacancy:Q",
                    title="Views / vacancy",
                    format=".2f",
                )
            )

        if "application_rate" in scatter_data.columns:
            tooltip_fields.append(
                alt.Tooltip(
                    "application_rate:Q",
                    title="Application rate",
                    format=".2%",
                )
            )

        if "opportunity_score" in scatter_data.columns:
            tooltip_fields.append(
                alt.Tooltip(
                    "opportunity_score:Q",
                    title="Opportunity score",
                    format=".1f",
                )
            )

        scatter = (
            alt.Chart(scatter_data)
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
                    if "seniority_group" in scatter_data.columns
                    else alt.value("#4C78A8")
                ),
                tooltip=tooltip_fields,
            )
            .properties(height=500)
            .interactive()
        )

        st.altair_chart(
            scatter,
            use_container_width=True,
        )


# ============================================================
# SKILLS & CATEGORIES
# ============================================================

with bridge_tab:

    st.caption(
        "These visuals use the separate bridge tables. "
        "For official multi-label Job Function analysis, use the category bridge. "
        "category_primary remains only for compatibility with the existing slicer."
    )

    filtered_job_ids = set(
        filtered["metadata_job_post_id"]
        .dropna()
        .astype(str)
        .tolist()
    ) if "metadata_job_post_id" in filtered.columns else set()

    category_bridge_view = (
        category_bridge[
            category_bridge["job_post_id"]
            .astype(str)
            .isin(filtered_job_ids)
        ]
        if filtered_job_ids
        else category_bridge.iloc[0:0]
    )

    skill_bridge_view = (
        skill_bridge[
            skill_bridge["job_post_id"]
            .astype(str)
            .isin(filtered_job_ids)
        ]
        if filtered_job_ids
        else skill_bridge.iloc[0:0]
    )

    bridge_left, bridge_right = st.columns(2)

    with bridge_left:
        st.subheader("Top Categories by Job Postings")

        if (
            not category_bridge.empty
            and "category_name" in category_bridge.columns
            and "job_post_id" in category_bridge.columns
        ):
            category_summary = (
                category_bridge_view
                .dropna(
                    subset=[
                        "category_name",
                        "job_post_id",
                    ]
                )
                .groupby(
                    "category_name",
                    observed=True,
                )["job_post_id"]
                .nunique()
                .sort_values(
                    ascending=False
                )
                .head(15)
                .rename("Job Postings")
                .reset_index()
                .rename(
                    columns={
                        "category_name": "Category"
                    }
                )
            )

            category_chart = (
                alt.Chart(category_summary)
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
                        alt.Tooltip(
                            "Category:N"
                        ),
                        alt.Tooltip(
                            "Job Postings:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=420
                )
            )

            st.altair_chart(
                category_chart,
                use_container_width=True,
            )

        else:
            st.info(
                "Category bridge is unavailable "
                "or expected columns are missing."
            )

    with bridge_right:
        st.subheader("Top Skills by Job Postings")

        if (
            not skill_bridge.empty
            and "skill_name" in skill_bridge.columns
            and "job_post_id" in skill_bridge.columns
        ):
            skill_summary = (
                skill_bridge_view
                .dropna(
                    subset=[
                        "skill_name",
                        "job_post_id",
                    ]
                )
                .groupby(
                    "skill_name",
                    observed=True,
                )["job_post_id"]
                .nunique()
                .sort_values(
                    ascending=False
                )
                .head(15)
                .rename("Job Postings")
                .reset_index()
                .rename(
                    columns={
                        "skill_name": "Skill"
                    }
                )
            )

            skill_chart = (
                alt.Chart(skill_summary)
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
                        alt.Tooltip(
                            "Skill:N"
                        ),
                        alt.Tooltip(
                            "Job Postings:Q",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=420
                )
            )

            st.altair_chart(
                skill_chart,
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

with quality_tab:

    st.caption(
        "Team 6 treatment is Preserve source, flag anomalies, verify with "
        "the source owner before changing values. Extreme does not automatically mean error."
    )

    q1, q2, q3, q4 = st.columns(4)

    q1.metric(
        "Rows Needing Source Review",
        fmt_number(
            filtered["needs_source_review"]
            .fillna(False)
            .astype(bool)
            .sum()
            if "needs_source_review" in filtered.columns
            else 0
        ),
    )

    q2.metric(
        "Data Quality Issue Rate",
        fmt_percent(data_quality_issue_rate),
    )

    q3.metric(
        "999 Vacancy Records",
        fmt_number(
            (filtered["number_of_vacancies"] == 999).sum()
            if "number_of_vacancies" in filtered.columns
            else 0
        ),
    )

    q4.metric(
        "RANDOM_JOB Records",
        fmt_number(
            filtered["job_id_format"]
            .astype(str)
            .eq("RANDOM_JOB")
            .sum()
            if "job_id_format" in filtered.columns
            else 0
        ),
    )

    st.subheader("Team 6 Outlier Review")

    outlier_rows = []

    def add_outlier_measure(area, rule, count):
        outlier_rows.append(
            {
                "Area": area,
                "Review rule": rule,
                "Matching rows": int(count),
            }
        )

    if "salary_minimum" in filtered.columns:
        add_outlier_measure(
            "Salary",
            "salary_minimum > S$50,000",
            (filtered["salary_minimum"] > 50_000).sum(),
        )
        add_outlier_measure(
            "Salary",
            "salary_minimum > S$100,000",
            (filtered["salary_minimum"] > 100_000).sum(),
        )
        add_outlier_measure(
            "Salary",
            "salary_minimum > S$200,000",
            (filtered["salary_minimum"] > 200_000).sum(),
        )

    if "minimum_years_experience" in filtered.columns:
        for threshold in [20, 30, 40, 50]:
            add_outlier_measure(
                "Experience",
                f"minimum experience > {threshold} years",
                (
                    filtered["minimum_years_experience"]
                    > threshold
                ).sum(),
            )

    if "number_of_vacancies" in filtered.columns:
        for threshold in [50, 100, 500]:
            add_outlier_measure(
                "Vacancies",
                f"vacancies > {threshold}",
                (
                    filtered["number_of_vacancies"]
                    > threshold
                ).sum(),
            )

        add_outlier_measure(
            "Vacancies",
            "vacancies = 999",
            (filtered["number_of_vacancies"] == 999).sum(),
        )

    if "job_id_format" in filtered.columns:
        add_outlier_measure(
            "Job ID",
            "RANDOM_JOB format",
            filtered["job_id_format"]
            .astype(str)
            .eq("RANDOM_JOB")
            .sum(),
        )

    if outlier_rows:
        st.dataframe(
            pd.DataFrame(outlier_rows),
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "Interpretation: these are review populations, not automatic deletions. "
        "Use median salary for broad summaries where extreme salaries distort the mean."
    )

    st.subheader("Inspect Flagged Records")

    outlier_view_options = [
        "All source-review flags",
        "Salary > 50,000",
        "Experience > 50 years",
        "Vacancies > 500",
        "Vacancies = 999",
        "RANDOM_JOB",
    ]

    selected_outlier_view = st.selectbox(
        "Review population",
        options=outlier_view_options,
        key="outlier_review_population",
    )

    outlier_mask = pd.Series(
        False,
        index=filtered.index,
    )

    if selected_outlier_view == "All source-review flags":
        if "needs_source_review" in filtered.columns:
            outlier_mask = (
                filtered["needs_source_review"]
                .fillna(False)
                .astype(bool)
            )

    elif selected_outlier_view == "Salary > 50,000":
        if (
            "salary_minimum" in filtered.columns
            and "salary_maximum" in filtered.columns
        ):
            outlier_mask = (
                (filtered["salary_minimum"] > 50_000)
                | (filtered["salary_maximum"] > 50_000)
            )

    elif selected_outlier_view == "Experience > 50 years":
        if "minimum_years_experience" in filtered.columns:
            outlier_mask = (
                filtered["minimum_years_experience"]
                > 50
            )

    elif selected_outlier_view == "Vacancies > 500":
        if "number_of_vacancies" in filtered.columns:
            outlier_mask = (
                filtered["number_of_vacancies"]
                > 500
            )

    elif selected_outlier_view == "Vacancies = 999":
        if "number_of_vacancies" in filtered.columns:
            outlier_mask = (
                filtered["number_of_vacancies"]
                == 999
            )

    elif selected_outlier_view == "RANDOM_JOB":
        if "job_id_format" in filtered.columns:
            outlier_mask = (
                filtered["job_id_format"]
                .astype(str)
                .eq("RANDOM_JOB")
            )

    flagged_columns = [
        c
        for c in [
            "metadata_job_post_id",
            "title_clean",
            "category_primary",
            "salary_minimum",
            "salary_maximum",
            "salary_midpoint",
            "minimum_years_experience",
            "number_of_vacancies",
            "job_id_format",
            "needs_source_review",
            "has_data_quality_issue",
        ]
        if c in filtered.columns
    ]

    flagged_records = (
        filtered.loc[
            outlier_mask,
            flagged_columns,
        ]
        .head(500)
    )

    st.caption(
        f"Showing up to 500 records from {int(outlier_mask.sum()):,} "
        "matching rows in the current filter context."
    )

    st.dataframe(
        flagged_records,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# REPOST ANALYSIS
# ============================================================

with repost_tab:

    st.caption(
        "Repost analysis is descriptive. A repost flag identifies repeat posting behaviour; "
        "it does not by itself explain why the job was reposted."
    )

    r1, r2, r3 = st.columns(3)

    reposted_jobs = (
        filtered["is_reposted"]
        .fillna(False)
        .astype(bool)
        .sum()
        if "is_reposted" in filtered.columns
        else 0
    )

    r1.metric(
        "Reposted Rows",
        fmt_number(reposted_jobs),
    )

    r2.metric(
        "Repost Rate",
        fmt_percent(repost_rate),
    )

    r3.metric(
        "Non-Reposted Rows",
        fmt_number(
            len(filtered) - reposted_jobs
        ),
    )

    if "is_reposted" in filtered.columns:
        repost_summary = (
            filtered["is_reposted"]
            .fillna(False)
            .map(
                {
                    True: "Reposted",
                    False: "Not Reposted",
                }
            )
            .value_counts()
            .rename_axis("Posting Status")
            .reset_index(name="Jobs")
        )

        repost_chart = (
            alt.Chart(repost_summary)
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
            repost_chart,
            use_container_width=True,
        )

    if (
        "is_reposted" in filtered.columns
        and "salary_midpoint" in filtered.columns
    ):
        repost_salary = (
            filtered.assign(
                posting_status=filtered["is_reposted"]
                .fillna(False)
                .map(
                    {
                        True: "Reposted",
                        False: "Not Reposted",
                    }
                )
            )
            .groupby(
                "posting_status",
                observed=True,
            )
            .agg(
                jobs=("salary_midpoint", "size"),
                average_salary=("salary_midpoint", "mean"),
                median_salary=("salary_midpoint", "median"),
            )
            .reset_index()
            .rename(
                columns={
                    "posting_status": "Posting Status",
                    "jobs": "Jobs",
                    "average_salary": "Average Salary",
                    "median_salary": "Median Salary",
                }
            )
        )

        st.dataframe(
            repost_salary,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# JOB RECORDS
# ============================================================

with records_tab:

    st.subheader("Filtered Job Records")

    rows_to_show = st.selectbox(
        "Rows to display",
        options=[25, 50, 100, 250, 500],
        index=2,
    )

    display_columns = [
        c
        for c in [
            "metadata_job_post_id",
            "title_clean",
            "employment_types",
            "category_primary",
            "seniority_group",
            "minimum_years_experience",
            "experience_band",
            "salary_minimum",
            "salary_maximum",
            "salary_midpoint",
            "salary_band",
            "number_of_vacancies",
            "vacancy_band",
            "applications_per_vacancy",
            "views_per_vacancy",
            "application_rate",
            "skill_tags",
            "posting_year",
            "month_year",
            "is_reposted",
            "needs_source_review",
            "opportunity_score",
            "opportunity_band",
        ]
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[
            display_columns
        ].head(rows_to_show),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("Job Drillthrough")

    if (
        "metadata_job_post_id" in filtered.columns
        and not filtered.empty
    ):
        drill_ids = (
            filtered["metadata_job_post_id"]
            .dropna()
            .astype(str)
            .head(10_000)
            .tolist()
        )

        selected_job_id = st.selectbox(
            "Select Job ID",
            options=drill_ids,
            key="drillthrough_job_id",
        )

        selected_job = filtered[
            filtered["metadata_job_post_id"]
            .astype(str)
            .eq(selected_job_id)
        ].head(1)

        if not selected_job.empty:
            row = selected_job.iloc[0]

            d1, d2, d3, d4 = st.columns(4)

            d1.metric(
                "Salary Midpoint",
                fmt_currency(
                    row.get(
                        "salary_midpoint",
                        float("nan"),
                    )
                ),
            )

            d2.metric(
                "Vacancies",
                fmt_number(
                    row.get(
                        "number_of_vacancies",
                        float("nan"),
                    )
                ),
            )

            d3.metric(
                "Applications / Vacancy",
                (
                    f"{row.get('applications_per_vacancy'):.2f}"
                    if pd.notna(
                        row.get(
                            "applications_per_vacancy",
                            float("nan"),
                        )
                    )
                    else "N/A"
                ),
            )

            d4.metric(
                "Opportunity Score",
                (
                    f"{row.get('opportunity_score'):.1f}"
                    if pd.notna(
                        row.get(
                            "opportunity_score",
                            float("nan"),
                        )
                    )
                    else "N/A"
                ),
            )

            detail_items = {
                col: row[col]
                for col in display_columns
                if col in row.index
            }

            st.json(
                {
                    key: (
                        None
                        if pd.isna(value)
                        else str(value)
                    )
                    for key, value in detail_items.items()
                }
            )

            job_category_rows = (
                category_bridge[
                    category_bridge["job_post_id"]
                    .astype(str)
                    .eq(selected_job_id)
                ][
                    [
                        c
                        for c in [
                            "job_post_id",
                            "category_name",
                        ]
                        if c in category_bridge.columns
                    ]
                ]
            )

            job_skill_rows = (
                skill_bridge[
                    skill_bridge["job_post_id"]
                    .astype(str)
                    .eq(selected_job_id)
                ][
                    [
                        c
                        for c in [
                            "job_post_id",
                            "skill_name",
                        ]
                        if c in skill_bridge.columns
                    ]
                ]
            )

            drill_left, drill_right = st.columns(2)

            with drill_left:
                st.write("**All Job Functions from bridge**")
                st.dataframe(
                    job_category_rows,
                    use_container_width=True,
                    hide_index=True,
                )

            with drill_right:
                st.write("**All Skills from bridge**")
                st.dataframe(
                    job_skill_rows,
                    use_container_width=True,
                    hide_index=True,
                )


# ============================================================
# TECHNICAL INFO
# ============================================================

with st.expander("Technical details"):

    st.write(
        {
            "data_file": str(DATA_FILE),
            "source_type": source_label,
            "rows": len(df),
            "loaded_columns": df.columns.tolist(),
            "filtered_rows": len(filtered),
            "v3_expected_rows": 1_044_597,
            "category_bridge_rows": len(category_bridge),
            "skill_bridge_rows": len(skill_bridge),
            "distinct_categories": distinct_categories,
            "distinct_skills": distinct_skills,
            "seniority_loaded": "seniority_group" in df.columns,
            "experience_band_loaded": "experience_band" in df.columns,
            "vacancy_band_loaded": "vacancy_band" in df.columns,
            "data_quality_flags_loaded": (
                "has_data_quality_issue" in df.columns
            ),
            "repost_flag_loaded": "is_reposted" in df.columns,
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
