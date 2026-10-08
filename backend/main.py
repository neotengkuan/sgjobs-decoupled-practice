"""
SGJobs decoupled practice - backend (FastAPI).

Run it from the project root:

    uvicorn backend.main:app --reload --port 8000

Then open http://localhost:8000/docs to see the API.

WHAT THIS FILE OWNS
------------------
* Data discovery and loading (parquet + the two bridge tables).
* The sidebar filter definitions, option lists and mask logic.
* The Overview KPI calculations.
* The Overview chart aggregations (grouped summaries, never raw rows).
* The Salary Analysis tab aggregations.
* The Opportunity Analysis tab aggregations.
* The Demand & Seniority tab aggregations (incl. the capped scatter
  sample).
* The Skills & Categories bridge aggregations.
* The Data Quality & Outlier counts and review populations.
* The Repost Analysis counts and aggregations.
* The Detail Drillthrough record, job-id and bridge lookups.
* Exposing all of it as JSON over HTTP.

ENDPOINTS
---------
* GET /api/health            -> cheap readiness check
* GET /api/filters           -> sidebar descriptors (label, key, options)
* GET /api/overview          -> Overview KPIs for a filter selection
* GET /api/overview/charts   -> Overview chart datasets, pre-aggregated
* GET /api/salary/analysis   -> Salary Analysis tab datasets, pre-aggregated
* GET /api/opportunity/analysis
                            -> Opportunity Analysis tab datasets, pre-aggregated
* GET /api/demand/analysis   -> Demand & Seniority tab datasets
* GET /api/skills-categories/analysis
                            -> Skills & Categories tab datasets (bridge)
* GET /api/data-quality/analysis
                            -> Data Quality & Outliers datasets
* GET /api/repost/analysis  -> Repost Analysis datasets
* GET /api/jobs            -> one page of matching job records (limit/offset)
* GET /api/jobs/ids        -> job-id selector options (capped, duplicates kept)
* GET /api/jobs/{job_post_id}
                            -> one job's detail record
* GET /api/jobs/{job_post_id}/categories
                            -> that job's category-bridge rows
* GET /api/jobs/{job_post_id}/skills
                            -> that job's skill-bridge rows

WHY THE LOGIC IS COPIED INSTEAD OF IMPORTED
--------------------------------------------
`app_deploy.py` is the untouched reference version and it is a Streamlit
script: importing it would execute the whole dashboard. Until the KPI and
filter code is extracted into a shared module (a later step), the reference
behaviour is duplicated here on purpose so the two versions can be compared
side by side.
"""

from __future__ import annotations

import math
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query

# ============================================================
# DATA SOURCES
# ============================================================
# Paths stay relative to the project root so the backend keeps reading
# the exact same data/ folder as app_deploy.py.

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"

PARQUET_FILE = DATA_DIR / "sgjob_v3_clean_features.parquet"
CSV_FILE = DATA_DIR / "sgjob_v3_clean_features.csv"
CSV_FALLBACK = CSV_FILE

CATEGORY_BRIDGE_PARQUET = DATA_DIR / "sgjob_v3_category_bridge.parquet"
CATEGORY_BRIDGE_FILE = DATA_DIR / "sgjob_v3_category_bridge.csv"

SKILL_BRIDGE_PARQUET = DATA_DIR / "sgjob_v3_skill_bridge.parquet"
SKILL_BRIDGE_FILE = DATA_DIR / "sgjob_v3_skill_bridge.csv"

DATA_CACHE_VERSION = "validated_v3_deploy_1"

# Bump this to invalidate the in-process cache after a data refresh.
CACHE_VERSION = DATA_CACHE_VERSION

EXPECTED_ROWS = 1_044_597


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


@lru_cache(maxsize=1)
def load_dashboard_data(path_string, wanted_columns, cache_version):
    """
    Load only the dashboard columns.
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
        data = pd.read_csv(path, usecols=usecols, low_memory=True)

    # --------------------------------------------------------
    # LIGHTWEIGHT DATA PREPARATION
    # --------------------------------------------------------
    # Same normalisation as the reference app, so the API returns
    # identical KPI values.

    for col in [
        "salary_midpoint",
        "number_of_vacancies",
        "opportunity_score",
        "posting_year",
        "month_year_sort",
    ]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    if "metadata_new_posting_date" in data.columns:
        data["metadata_new_posting_date"] = pd.to_datetime(
            data["metadata_new_posting_date"],
            errors="coerce",
        )

    if (
        "posting_year" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["posting_year"] = data["metadata_new_posting_date"].dt.year

    if (
        "month_year" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["month_year"] = (
            data["metadata_new_posting_date"]
            .dt.to_period("M")
            .astype("string")
        )

    if (
        "month_year_sort" not in data.columns
        and "metadata_new_posting_date" in data.columns
    ):
        data["month_year_sort"] = (
            data["metadata_new_posting_date"].dt.year * 100
            + data["metadata_new_posting_date"].dt.month
        )

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


@lru_cache(maxsize=1)
def load_category_bridge(cache_version):
    """Load only the two columns needed for category analysis."""
    required = ["job_post_id", "category_name"]

    if CATEGORY_BRIDGE_PARQUET.exists():
        return pd.read_parquet(CATEGORY_BRIDGE_PARQUET, columns=required)

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


@lru_cache(maxsize=1)
def load_skill_bridge(cache_version):
    """Load only the two columns needed for skill analysis."""
    required = ["job_post_id", "skill_name"]

    if SKILL_BRIDGE_PARQUET.exists():
        return pd.read_parquet(SKILL_BRIDGE_PARQUET, columns=required)

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


# ============================================================
# COLUMNS NEEDED BY THE KPIs AND THE FILTERS
# ============================================================
# Subset of app_deploy.py's WANTED_COLUMNS: only the fields the
# Overview KPIs and the sidebar filters touch. The remaining columns
# come back with the chart endpoints.

OVERVIEW_COLUMNS = (
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

    # Time
    "posting_year",
    "month_year",
    "month_year_sort",
    "metadata_new_posting_date",

    # Detail drillthrough convenience field
    "skill_tags",

    # Team 6 review / data-quality fields
    "job_id_format",
    "needs_source_review",
    "has_data_quality_issue",
    "is_reposted",
)


# ============================================================
# FILTER SPECIFICATION
# ============================================================
# Single source of truth for the sidebar filters. The frontend renders
# these descriptors verbatim, so labels, ordering rules and state keys
# stay in sync with app_deploy.py without duplicating them there.
#
#   param        -> the query parameter name used on /api/overview
#   column       -> the column/field the values are matched against
#   label        -> the sidebar label (unchanged from app_deploy.py)
#   state_key    -> Streamlit widget key (unchanged from app_deploy.py)
#   source       -> which loaded frame owns the field
#   order        -> how the option list is built:
#                     "sorted"    -> alphabetical (app_deploy default)
#                     "appearance"-> first-seen order, as stored
#                     "preferred" -> business order first, rest alphabetical
#   option_dtype -> numeric option cast (posting_year)
#   coerce       -> cast applied to incoming query values
#   help         -> optional widget help text

FILTER_SPECS = (
    {
        "param": "employment_types",
        "column": "employment_types",
        "label": "Employment Type",
        "state_key": "employment_filter",
        "source": "df",
        "order": "sorted",
    },
    {
        "param": "category_primary",
        "column": "category_primary",
        "label": "Job Function",
        "state_key": "job_function_filter",
        "source": "df",
        "order": "sorted",
    },
    {
        "param": "category_bridge",
        "column": "category_name",
        "label": "Job Function (Bridge)",
        "state_key": "category_bridge_filter",
        "source": "category_bridge",
        "order": "sorted",
        "help": (
            "Recommended for official Job Function analysis. "
            "A job can belong to more than one Job Function."
        ),
    },
    {
        "param": "skill_bridge",
        "column": "skill_name",
        "label": "Skill",
        "state_key": "skill_bridge_filter",
        "source": "skill_bridge",
        "order": "sorted",
    },
    {
        "param": "seniority_group",
        "column": "seniority_group",
        "label": "Seniority",
        "state_key": "seniority_filter",
        "source": "df",
        "order": "sorted",
    },
    {
        "param": "experience_band",
        "column": "experience_band",
        "label": "Experience Band",
        "state_key": "experience_band_filter",
        "source": "df",
        "order": "appearance",
    },
    {
        "param": "vacancy_band",
        "column": "vacancy_band",
        "label": "Vacancy Band",
        "state_key": "vacancy_band_filter",
        "source": "df",
        "order": "appearance",
    },
    {
        "param": "salary_band",
        "column": "salary_band",
        "label": "Salary Band",
        "state_key": "salary_band_filter",
        "source": "df",
        "order": "preferred",
        "preferred": [
            "< 3K",
            "3K–5K",
            "5K–7K",
            "7K–10K",
            "10K+",
            "Unknown",
        ],
    },
    {
        "param": "opportunity_band",
        "column": "opportunity_band",
        "label": "Opportunity Band",
        "state_key": "opportunity_band_filter",
        "source": "df",
        "order": "preferred",
        "preferred": [
            "Low",
            "Moderate",
            "Good",
            "High",
        ],
    },
    {
        "param": "posting_year",
        "column": "posting_year",
        "label": "Posting Year",
        "state_key": "posting_year_filter",
        "source": "df",
        "order": "sorted",
        "option_dtype": int,
        "coerce": int,
    },
)


@lru_cache(maxsize=1)
def load_overview_context():
    """
    Load and normalise everything the Overview KPIs need, once per process.

    Returns a dict so the endpoint code stays declarative.
    """
    started = time.perf_counter()

    data_file = first_existing_path()

    if data_file is None:
        raise FileNotFoundError(
            "No deployment data file was found. Expected inside the "
            "repository data/ folder: "
            "data/sgjob_v3_clean_features.parquet or "
            "data/sgjob_v3_clean_features.csv"
        )

    df = load_dashboard_data(
        str(data_file),
        OVERVIEW_COLUMNS,
        CACHE_VERSION,
    )

    category_bridge = load_category_bridge(CACHE_VERSION)
    skill_bridge = load_skill_bridge(CACHE_VERSION)

    for frame, column in [
        (category_bridge, "category_name"),
        (skill_bridge, "skill_name"),
    ]:
        if not frame.empty and column in frame.columns:
            frame[column] = frame[column].astype("category")

    elapsed = time.perf_counter() - started

    print(
        f"[data] loaded {len(df):,} rows / {len(df.columns)} columns from "
        f"{data_file.name} in {elapsed:.1f}s",
        flush=True,
    )

    return {
        "df": df,
        "category_bridge": category_bridge,
        "skill_bridge": skill_bridge,
        "data_file_name": data_file.name,
        "source_type": (
            "Parquet"
            if data_file.suffix.lower() == ".parquet"
            else "CSV"
        ),
        "load_seconds": round(elapsed, 2),
    }


# ============================================================
# JSON SANITISERS
# ============================================================
# NaN and +/-inf are not valid JSON, so they travel as null and the
# frontend renders them as "N/A" exactly like app_deploy.py does.

def as_count(value):
    """Whole-number measure (row counts, sums of vacancies, nunique)."""
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return int(round(number))


def as_ratio(value):
    """Continuous measure (salary averages, rates, scores)."""
    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if math.isnan(number) or math.isinf(number):
        return None

    return number


# ============================================================
# FILTER ENGINE
# ============================================================
# All filtering lives here. The frontend only sends the selected
# values, so this is the only place that decides what a filter means.


def build_filter_options(spec, source):
    """
    Build one filter's option list, following app_deploy.py's rules.
    """
    column = spec["column"]

    # Numeric options (Posting Year) skip the string casting.
    if spec.get("option_dtype") is int:
        values = source[column].dropna().astype(int).unique().tolist()
        return sorted(values)

    order = spec.get("order", "sorted")

    if order == "appearance":
        return (
            source[column]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
        )

    actual = set(
        source[column]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if order == "preferred":
        preferred = [
            value
            for value in spec["preferred"]
            if value in actual
        ]
        return preferred + sorted(actual - set(preferred))

    return sorted(actual)


@lru_cache(maxsize=1)
def get_filter_descriptors():
    """
    Sidebar metadata the frontend renders. Cached because the option
    lists only change when the loaded data changes.
    """
    context = load_overview_context()

    descriptors = []

    for spec in FILTER_SPECS:
        source = context[spec["source"]]
        column = spec["column"]

        available = (
            not source.empty
            and column in source.columns
        )

        descriptors.append(
            {
                "param": spec["param"],
                "label": spec["label"],
                "state_key": spec["state_key"],
                "help": spec.get("help"),
                "available": available,
                "options": (
                    build_filter_options(spec, source)
                    if available
                    else []
                ),
            }
        )

    return descriptors


def validate_selections(context, raw_selections):
    """
    Turn raw query values into a validated {param: [values]} dict.

    Unknown filters, filters the loaded data cannot support and
    unparsable numbers are rejected with 422 instead of silently
    returning wrong KPIs.
    """
    selections = {}

    for spec in FILTER_SPECS:
        raw = raw_selections.get(spec["param"]) or []

        if not raw:
            continue

        source = context[spec["source"]]
        column = spec["column"]

        if source.empty or column not in source.columns:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{spec['label']}' cannot be filtered because "
                    f"'{column}' is not available in the loaded data."
                ),
            )

        if spec["source"] != "df" and (
            "metadata_job_post_id" not in context["df"].columns
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"'{spec['label']}' cannot be filtered because "
                    "'metadata_job_post_id' is not available "
                    "in the loaded data."
                ),
            )

        caster = spec.get("coerce")

        if caster is None:
            selections[spec["param"]] = [str(value) for value in raw]
            continue

        coerced = []

        for value in raw:
            try:
                coerced.append(caster(value))
            except (TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"'{spec['label']}' received an invalid value: "
                        f"{value!r}"
                    ),
                ) from error

        selections[spec["param"]] = coerced

    return selections


def apply_filters(context, selections):
    """
    Build the filter mask exactly like app_deploy.py does: start from
    all True, AND one isin() mask per active filter, then slice.
    """
    df = context["df"]

    mask = pd.Series(True, index=df.index)

    for spec in FILTER_SPECS:
        selected = selections.get(spec["param"])

        if not selected:
            continue

        if spec["source"] == "df":
            mask &= df[spec["column"]].isin(selected)
            continue

        # Bridge filters match on job id, because a job can carry
        # several categories/skills at once.
        source = context[spec["source"]]

        matching_job_ids = (
            source.loc[
                source[spec["column"]]
                .astype(str)
                .isin(selected),
                "job_post_id",
            ]
            .dropna()
            .astype(str)
            .unique()
        )

        mask &= (
            df["metadata_job_post_id"]
            .astype(str)
            .isin(matching_job_ids)
        )

    return df.loc[mask]


def describe_selections(selections):
    """One-line summary of the active filters, shown under the KPIs."""
    if not selections:
        return "All records (no filters applied)."

    parts = []

    for spec in FILTER_SPECS:
        values = selections.get(spec["param"])

        if not values:
            continue

        shown = ", ".join(str(value) for value in values[:3])

        if len(values) > 3:
            shown += f", +{len(values) - 3} more"

        parts.append(f"{spec['label']}: {shown}")

    return " | ".join(parts)


# ============================================================
# OVERVIEW KPI CALCULATIONS
# ============================================================
# Logic copied from app_deploy.py and applied to the filtered frame
# exactly as the reference app does.


def calculate_overview_kpis(selections=None):
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)
    category_bridge = context["category_bridge"]
    skill_bridge = context["skill_bridge"]

    # --------------------------------------------------------
    # PRIMARY KPI CARDS
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # POWER BI / DAX-EQUIVALENT MEASURES
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # BRIDGE-TABLE MEASURES
    # --------------------------------------------------------
    # NOTE: app_deploy.py measures these on the FULL bridge tables,
    # not on the filtered subset, so the four bridge KPI cards do
    # not change when a Job Function (Bridge) or Skill filter is
    # applied. Kept identical here on purpose; only the main KPI
    # cards above are filter-aware.

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

    return {
        "meta": {
            "source": "api",
            "endpoint": "/api/overview",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "data_file": context["data_file_name"],
            "source_type": context["source_type"],
            "rows_total": len(context["df"]),
            "columns_loaded": context["df"].columns.tolist(),
            "rows_filtered": len(filtered),
            "load_seconds": context["load_seconds"],
            "category_bridge_rows": len(category_bridge),
            "skill_bridge_rows": len(skill_bridge),
            "v3_expected_rows": EXPECTED_ROWS,
        },
        "primary_kpis": {
            "total_jobs": as_count(total_jobs),
            "average_salary": as_ratio(average_salary),
            "median_salary": as_ratio(median_salary),
            "total_vacancies": as_count(total_vacancies),
            "avg_opportunity": as_ratio(avg_opportunity),
        },
        "bridge_kpis": {
            "distinct_categories": as_count(distinct_categories),
            "category_job_postings": as_count(category_job_postings),
            "distinct_skills": as_count(distinct_skills),
            "skill_job_postings": as_count(skill_job_postings),
        },
        "dax_measures": {
            "unique_job_postings": as_count(unique_job_postings),
            "total_applications": as_count(total_applications),
            "average_application_rate": as_ratio(average_application_rate),
            "average_applications_per_vacancy": as_ratio(
                average_applications_per_vacancy
            ),
            "average_views_per_vacancy": as_ratio(average_views_per_vacancy),
            "average_minimum_experience": as_ratio(
                average_minimum_experience
            ),
            "overall_applications_per_vacancy": as_ratio(
                overall_applications_per_vacancy
            ),
            "high_opportunity_jobs": as_count(high_opportunity_jobs),
            "data_quality_issue_rate": as_ratio(data_quality_issue_rate),
            "repost_rate": as_ratio(repost_rate),
        },
    }


# ============================================================
# OVERVIEW CHART AGGREGATIONS
# ============================================================
# The four Overview charts from app_deploy.py, aggregated here so the
# frontend never receives raw records. Each function returns
# {"available": bool, "data": [row, ...]} where the row keys are the
# exact field names the reference charts encode, so the Altair specs in
# the frontend can stay identical to the reference ones.
#
# `available` reproduces the reference's render condition, so a chart
# is skipped exactly when app_deploy.py skips it. Chart titles and
# tooltips stay in the frontend with the reference literals.


def json_number(value):
    """Chart value that survives JSON: int when whole, float otherwise."""
    number = float(value)

    if math.isnan(number) or math.isinf(number):
        return None

    return int(number) if number.is_integer() else number


def band_counts(filtered, column, label):
    """
    Job counts per categorical band column, as the reference charts do it.

    Shared by the Employment Type, Salary Band and Opportunity Band
    charts: same value_counts(dropna=True) call, same "Jobs" column, only
    the column and the axis label change. Keeping one implementation stops
    the three tabs from drifting apart.

    NOTE: these columns are categorical, so value_counts keeps
    zero-count categories, exactly as the reference charts do. Do not
    "fix" that here without changing app_deploy.py too.
    """
    return (
        filtered[column]
        .value_counts(dropna=True)
        .rename_axis(label)
        .reset_index(name="Jobs")
    )


def band_chart(filtered, column, label):
    """
    A band-count chart payload, e.g.
    {"available": True, "data": [{"<label>": "...", "Jobs": 1}]}
    """
    available = (
        column in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

    summary = band_counts(filtered, column, label)

    return {
        "available": True,
        "data": [
            {
                label: str(record[label]),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def category_counts(filtered):
    """
    Job counts per category_primary.

    Shared by the Overview "Top 15 Job Functions" chart and the Salary
    "Average Salary by Job Function" chart, because the reference picks
    its top 15 job functions with this exact value_counts call in both
    places. Reusing it keeps the two selections identical.
    """
    return filtered["category_primary"].value_counts(dropna=True)


def employment_type_chart(filtered):
    """
    Jobs by Employment Type - value_counts on employment_types.
    """
    return band_chart(
        filtered,
        column="employment_types",
        label="Employment Type",
    )


def top_job_functions_chart(filtered):
    """
    Top 15 Job Functions - value_counts on category_primary, head(15).

    Same categorical caveat as employment_type_chart.
    """
    available = (
        "category_primary" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

    summary = (
        category_counts(filtered)
        .head(15)
        .rename_axis("Job Function")
        .reset_index(name="Jobs")
    )

    return {
        "available": True,
        "data": [
            {
                "Job Function": str(record["Job Function"]),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def jobs_over_time_chart(filtered):
    """
    Jobs Over Time - monthly counts, sorted by month_year_sort.
    """
    available = (
        "month_year" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

    if "month_year_sort" in filtered.columns:
        summary = (
            filtered[["month_year", "month_year_sort"]]
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

    # month_year_sort is the sort key, already applied above; it is not
    # encoded by the reference chart so it is not sent either.
    return {
        "available": True,
        "data": [
            {
                "month_year": str(record["month_year"]),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def top_job_functions_by_vacancies_chart(filtered):
    """
    Top 10 Job Functions by Vacancies - sum of number_of_vacancies by
    category_primary.
    """
    available = (
        "category_primary" in filtered.columns
        and "number_of_vacancies" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

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

    return {
        "available": True,
        "data": [
            {
                "Job Function": str(record["Job Function"]),
                "Vacancies": json_number(record["Vacancies"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def calculate_overview_charts(selections=None):
    """
    Pre-aggregated datasets for the four Overview charts, computed from
    the same filtered frame the KPIs use.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    return {
        "meta": {
            "endpoint": "/api/overview/charts",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
        },
        "charts": {
            "employment_type": employment_type_chart(filtered),
            "top_job_functions": top_job_functions_chart(filtered),
            "jobs_over_time": jobs_over_time_chart(filtered),
            "top_job_functions_by_vacancies": (
                top_job_functions_by_vacancies_chart(filtered)
            ),
        },
    }


# ============================================================
# SALARY ANALYSIS AGGREGATIONS
# ============================================================
# The three blocks of the Salary Analysis tab in app_deploy.py:
#   1. Jobs by Salary Band          -> salary_band_chart
#   2. Average Salary by Job Function -> average_salary_by_job_function_chart
#   3. Salary Summary               -> salary_summary
#
# category_counts() (top 15 job functions) is defined with the other
# shared chart helpers above.


def salary_band_chart(filtered):
    """
    Jobs by Salary Band - value_counts on salary_band.

    Same categorical caveat as employment_type_chart: zero-count bands
    are kept, matching the reference.
    """
    return band_chart(
        filtered,
        column="salary_band",
        label="Salary Band",
    )


def average_salary_by_job_function_chart(filtered):
    """
    Average Salary by Job Function - mean salary_midpoint for the top
    15 job functions by job count.
    """
    available = (
        "category_primary" in filtered.columns
        and "salary_midpoint" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

    top_functions = category_counts(filtered).head(15).index

    summary = (
        filtered[
            filtered["category_primary"].isin(top_functions)
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

    return {
        "available": True,
        "data": [
            {
                "Job Function": str(record["Job Function"]),
                "Average Salary": json_number(record["Average Salary"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def salary_summary(filtered):
    """
    Salary Summary table - the five measures app_deploy.py builds with
    salary_midpoint. Raw values only; the reference's currency
    formatting is applied in the frontend, like every other KPI.
    """
    available = (
        "salary_midpoint" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False}

    salary_series = filtered["salary_midpoint"]

    return {
        "available": True,
        "jobs_with_salary_data": as_count(salary_series.notna().sum()),
        "average_salary": as_ratio(salary_series.mean()),
        "median_salary": as_ratio(salary_series.median()),
        "minimum_salary_midpoint": as_ratio(salary_series.min()),
        "maximum_salary_midpoint": as_ratio(salary_series.max()),
    }


def calculate_salary_analysis(selections=None):
    """
    Datasets for the Salary Analysis tab, computed from the same
    filtered frame the KPIs and Overview charts use.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    return {
        "meta": {
            "endpoint": "/api/salary/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
        },
        "salary_band_counts": salary_band_chart(filtered),
        "average_salary_by_job_function": (
            average_salary_by_job_function_chart(filtered)
        ),
        "summary": salary_summary(filtered),
    }


# ============================================================
# OPPORTUNITY ANALYSIS AGGREGATIONS
# ============================================================
# The two blocks of the Opportunity Analysis tab in app_deploy.py:
#   1. Jobs by Opportunity Band    -> opportunity_band_chart
#   2. Top Job Functions by Opportunity Score
#                                   -> top_job_functions_by_opportunity_chart
#
# OPPORTUNITY SCORE
# -----------------
# opportunity_score is a pre-computed column in the V3 dataset. Nothing
# here re-derives it: no weights, no formula, no rescaling. These
# functions only group and average the value exactly as the reference
# does, so the score definition stays owned by the dataset.


def opportunity_band_chart(filtered):
    """
    Jobs by Opportunity Band - value_counts on opportunity_band.
    """
    return band_chart(
        filtered,
        column="opportunity_band",
        label="Opportunity Band",
    )


def opportunity_min_jobs(filtered_row_count):
    """
    Sample-size floor for the job-function ranking.

    Kept from the reference so tiny filtered selections cannot be
    dominated by one- or two-job categories, while still allowing a
    ranking to be shown at all on small selections.
    """
    if filtered_row_count >= 5_000:
        return 100

    return max(5, int(filtered_row_count * 0.02))


def top_job_functions_by_opportunity_chart(filtered):
    """
    Top Job Functions by Opportunity Score - mean opportunity_score and
    job count per job function, restricted to the top 15.

    Returns the ranking decision as well as the rows, because the
    reference shows a different caption depending on which branch it
    took: min_jobs is the sample-size floor that was applied, and
    fallback_applied says the floor was impossible to satisfy so every
    available job function is shown instead.
    """
    available = (
        "category_primary" in filtered.columns
        and "opportunity_score" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {
            "available": False,
            "data": [],
            "min_jobs": None,
            "fallback_applied": False,
        }

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
            average_opportunity=("opportunity_score", "mean"),
            jobs=("opportunity_score", "size"),
        )
        .reset_index()
    )

    min_jobs = opportunity_min_jobs(len(filtered))

    ranked = summary[summary["jobs"] >= min_jobs].copy()

    # If no category passes the adaptive threshold, show the available
    # categories rather than rendering a blank panel.
    fallback_applied = bool(ranked.empty and not summary.empty)

    if fallback_applied:
        ranked = summary.copy()

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

    return {
        "available": True,
        "min_jobs": min_jobs,
        "fallback_applied": fallback_applied,
        "data": [
            {
                "Job Function": str(record["Job Function"]),
                "Average Opportunity Score": json_number(
                    record["Average Opportunity Score"]
                ),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def calculate_opportunity_analysis(selections=None):
    """
    Datasets for the Opportunity Analysis tab. One filtered frame is
    built and handed to both blocks, so the two charts always describe
    the same rows.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    return {
        "meta": {
            "endpoint": "/api/opportunity/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
        },
        "opportunity_band_counts": opportunity_band_chart(filtered),
        "top_job_functions": top_job_functions_by_opportunity_chart(filtered),
    }


# ============================================================
# DEMAND & SENIORITY AGGREGATIONS
# ============================================================
# The three blocks of the Demand & Seniority tab in app_deploy.py:
#   1. Jobs by Seniority            -> seniority_chart
#   2. Average Salary by Seniority  -> average_salary_by_seniority_chart
#   3. Salary vs Applications per Vacancy -> salary_vs_applications_scatter
#
# The scatter is the one place in this API where rows cross the wire
# instead of aggregates: a scatter plot cannot be drawn from summaries.
# It is therefore hard-capped at the reference's 25,000 rows and
# sampled with the reference's seed, so the payload stays bounded. Lower
# SGJOBS_SCATTER_SAMPLE_LIMIT to shrink it further.

SCATTER_SAMPLE_LIMIT = int(os.getenv("SGJOBS_SCATTER_SAMPLE_LIMIT", "25000"))
SCATTER_SAMPLE_SEED = 42

# Columns the reference scatter encodes and always drops nulls for.
SCATTER_REQUIRED_COLUMNS = (
    "salary_midpoint",
    "applications_per_vacancy",
    "number_of_vacancies",
)

# Every column the reference scatter can use, in its own order.
SCATTER_COLUMNS = (
    "metadata_job_post_id",
    "category_primary",
    "seniority_group",
    "salary_midpoint",
    "number_of_vacancies",
    "applications_per_vacancy",
    "views_per_vacancy",
    "application_rate",
    "opportunity_score",
)


def json_value(value):
    """One JSON-safe cell: numbers stay numeric, text stays text, gaps null."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return json_number(value)

    return str(value)


def seniority_chart(filtered):
    """
    Jobs by Seniority - value_counts on seniority_group.

    Note the reference's axis title here is "Job Postings", not the
    "Number of Jobs" used by the other count charts.
    """
    return band_chart(
        filtered,
        column="seniority_group",
        label="Seniority",
    )


def average_salary_by_seniority_chart(filtered):
    """
    Average Salary by Seniority - mean, median and job count per
    seniority group.
    """
    available = (
        "seniority_group" in filtered.columns
        and "salary_midpoint" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {"available": False, "data": []}

    summary = (
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

    return {
        "available": True,
        "data": [
            {
                "Seniority": str(record["Seniority"]),
                "Average Salary": json_number(record["Average Salary"]),
                "Median Salary": json_number(record["Median Salary"]),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def salary_vs_applications_scatter(filtered):
    """
    Salary vs Applications per Vacancy.

    Row-level by nature, so the reference caps it at 25,000 rows with a
    fixed seed. This returns the capped sample plus the `fields` that
    actually survived, so the frontend can build the reference's
    conditional tooltip list without inspecting the data.

    Availability follows the reference exactly: the three encoded
    columns must exist, but an empty result is still rendered as an
    empty chart rather than hidden.
    """
    available = all(
        column in filtered.columns
        for column in SCATTER_REQUIRED_COLUMNS
    )

    if not available:
        return {
            "available": False,
            "fields": [],
            "data": [],
            "sampled": False,
            "rows_before_sample": 0,
            "rows_sampled": 0,
        }

    scatter_data = (
        filtered[
            [
                column
                for column in SCATTER_COLUMNS
                if column in filtered.columns
            ]
        ]
        .replace(
            [float("inf"), float("-inf")],
            pd.NA,
        )
        .dropna(subset=list(SCATTER_REQUIRED_COLUMNS))
    )

    rows_before_sample = len(scatter_data)
    sampled = False

    # Keep browser rendering responsive without changing KPI calculations.
    if rows_before_sample > SCATTER_SAMPLE_LIMIT:
        scatter_data = scatter_data.sample(
            SCATTER_SAMPLE_LIMIT,
            random_state=SCATTER_SAMPLE_SEED,
        )
        sampled = True

    fields = scatter_data.columns.tolist()

    return {
        "available": True,
        "fields": fields,
        "sampled": sampled,
        "rows_before_sample": rows_before_sample,
        "rows_sampled": len(scatter_data),
        "data": [
            {
                field: json_value(record[field])
                for field in fields
            }
            for record in scatter_data.to_dict(orient="records")
        ],
    }


def calculate_demand_analysis(selections=None):
    """
    Datasets for the Demand & Seniority tab, from one filtered frame so
    the two bar charts and the scatter always describe the same rows.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    return {
        "meta": {
            "endpoint": "/api/demand/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
            "scatter_sample_limit": SCATTER_SAMPLE_LIMIT,
        },
        "seniority_counts": seniority_chart(filtered),
        "average_salary_by_seniority": (
            average_salary_by_seniority_chart(filtered)
        ),
        "salary_vs_applications": salary_vs_applications_scatter(filtered),
    }


# ============================================================
# SKILLS & CATEGORIES AGGREGATIONS (BRIDGE TABLES)
# ============================================================
# The two charts of the Skills & Categories tab in app_deploy.py.
#
# METRIC DEFINITION
# -----------------
# Both charts count DISTINCT job postings: the bridge tables are
# multi-label (one job can carry several categories and several
# skills), so the ranking groups by name and takes nunique() on
# job_post_id. A job with 4 skills therefore adds 1 to each of its 4
# skill rows and is never counted twice for the same skill.
#
# The job-id set of the current filter selection is built once and
# reused for both bridges, and the bridge filtering by job_post_id
# stays in the backend.


def filtered_job_ids(context, filtered):
    """
    The distinct job ids in the current filter selection.

    Built once per request and reused by both bridge charts. A set, so
    duplicate job rows in the main table collapse to one id here.
    """
    if "metadata_job_post_id" not in filtered.columns:
        return set()

    return set(
        filtered["metadata_job_post_id"]
        .dropna()
        .astype(str)
        .tolist()
    )


def bridge_view(context, key, job_ids):
    """
    The bridge rows belonging to the current filter selection.

    An empty selection yields an empty view rather than the whole
    bridge, matching the reference.
    """
    frame = context[key]

    if not job_ids:
        return frame.iloc[0:0]

    return frame[
        frame["job_post_id"]
        .astype(str)
        .isin(job_ids)
    ]


def bridge_available(context, key, name_column):
    """
    The reference checks the FULL bridge table for availability, not the
    filtered view. So a filter that selects no jobs still renders an
    empty chart instead of the "bridge unavailable" info message.
    """
    frame = context[key]

    return (
        not frame.empty
        and name_column in frame.columns
        and "job_post_id" in frame.columns
    )


def top_bridge_names(view, name_column, label):
    """
    Top 15 names by distinct job postings.
    """
    summary = (
        view
        .dropna(
            subset=[
                name_column,
                "job_post_id",
            ]
        )
        .groupby(
            name_column,
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
                name_column: label,
            }
        )
    )

    return {
        "available": True,
        "data": [
            {
                label: str(record[label]),
                "Job Postings": json_number(record["Job Postings"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def top_categories_chart(context, job_ids):
    """
    Top Categories by Job Postings - distinct job postings per official
    Job Function from the category bridge.
    """
    if not bridge_available(context, "category_bridge", "category_name"):
        return {"available": False, "data": []}

    view = bridge_view(context, "category_bridge", job_ids)

    return top_bridge_names(view, "category_name", "Category")


def top_skills_chart(context, job_ids):
    """
    Top Skills by Job Postings - distinct job postings per skill from
    the skill bridge.
    """
    if not bridge_available(context, "skill_bridge", "skill_name"):
        return {"available": False, "data": []}

    view = bridge_view(context, "skill_bridge", job_ids)

    return top_bridge_names(view, "skill_name", "Skill")


def calculate_skills_categories_analysis(selections=None):
    """
    Datasets for the Skills & Categories tab. The filtered job-id set is
    built once and shared by both bridge charts.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    job_ids = filtered_job_ids(context, filtered)

    return {
        "meta": {
            "endpoint": "/api/skills-categories/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
            "filtered_job_ids": len(job_ids),
            "count_metric": "distinct job postings (nunique of job_post_id)",
        },
        "top_categories": top_categories_chart(context, job_ids),
        "top_skills": top_skills_chart(context, job_ids),
    }


# ============================================================
# DATA QUALITY & OUTLIERS
# ============================================================
# The Data Quality & Outliers tab in app_deploy.py: four metric cards,
# the Team 6 outlier rule table, and the "Inspect Flagged Records"
# table driven by a review-population selector.
#
# TEAM 6 TREATMENT (PRESERVED)
# -----------------------------
# "Preserve source, flag anomalies, verify with the source owner before
# changing values." Nothing here deletes, clips, caps or rewrites a
# value. Extreme does not automatically mean error: the outlier rules
# only COUNT matching rows, and every matching row is still returned to
# the review table so a human can judge it.
#
# The tab deliberately re-derives every count from the raw columns
# (salary_minimum, number_of_vacancies, ...) instead of trusting the
# dataset's own *_review_flag columns, and so does this module. Do not
# "simplify" it by switching to those flags: the numbers would change.
#
# DENOMINATOR
# -----------
# Data Quality Issue Rate = flagged rows / total filtered rows. The
# counts below are row counts over the same filtered frame.

QUALITY_SALARY_THRESHOLD = 50_000
QUALITY_EXPERIENCE_THRESHOLD = 50
QUALITY_VACANCY_THRESHOLD = 500

# Vacancy count treated as a review population rather than a real head
# count. Kept as-is: these rows are counted and shown, never corrected.
QUALITY_SENTINEL_VACANCY = 999

SALARY_REVIEW_THRESHOLDS = (50_000, 100_000, 200_000)
EXPERIENCE_REVIEW_THRESHOLDS = (20, 30, 40, 50)
VACANCY_REVIEW_THRESHOLDS = (50, 100, 500)

# Rows of the review table returned to the frontend. The reference caps
# at 500 as well; lower with SGJOBS_FLAGGED_RECORD_LIMIT if needed.
FLAGGED_RECORD_LIMIT = int(os.getenv("SGJOBS_FLAGGED_RECORD_LIMIT", "500"))

# The review-population selector. The labels are the wire values the
# frontend sends back, and the first entry is the default, exactly like
# the reference selectbox which has no explicit index.
QUALITY_REVIEW_POPULATIONS = (
    {
        "value": "All source-review flags",
        "kind": "source_review_flags",
    },
    {
        "value": "Salary > 50,000",
        "kind": "salary_over_threshold",
    },
    {
        "value": "Experience > 50 years",
        "kind": "experience_over_threshold",
    },
    {
        "value": "Vacancies > 500",
        "kind": "vacancies_over_threshold",
    },
    {
        "value": "Vacancies = 999",
        "kind": "vacancies_sentinel",
    },
    {
        "value": "RANDOM_JOB",
        "kind": "random_job_format",
    },
)

# Columns of the review table, in the reference's order.
FLAGGED_RECORD_COLUMNS = (
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
)


def flag_series(series):
    """The reference's fillna(False).astype(bool) flag coercion."""
    return series.fillna(False).astype(bool)


def vacancy_sentinel_count(filtered):
    """Rows carrying the 999 vacancy sentinel. Used by a KPI and a rule."""
    if "number_of_vacancies" not in filtered.columns:
        return 0

    return int(
        (filtered["number_of_vacancies"] == QUALITY_SENTINEL_VACANCY)
        .sum()
    )


def random_job_count(filtered):
    """Rows with the RANDOM_JOB id format. Used by a KPI and a rule."""
    if "job_id_format" not in filtered.columns:
        return 0

    return int(
        filtered["job_id_format"]
        .astype(str)
        .eq("RANDOM_JOB")
        .sum()
    )


def resolve_review_population(value):
    """
    Validate the requested review population and return its spec.

    A missing value means "the first one", matching the reference
    selectbox default.
    """
    if value is None:
        return QUALITY_REVIEW_POPULATIONS[0]

    for spec in QUALITY_REVIEW_POPULATIONS:
        if spec["value"] == value:
            return spec

    raise HTTPException(
        status_code=422,
        detail=(
            f"Unknown review population: {value!r}. "
            f"Expected one of: "
            f"{', '.join(s['value'] for s in QUALITY_REVIEW_POPULATIONS)}"
        ),
    )


def review_population_mask(filtered, kind):
    """
    The reference's outlier_mask for one review population. A population
    whose columns are missing falls back to an all-False mask, so the
    table renders empty instead of erroring.
    """
    empty = pd.Series(False, index=filtered.index)

    if kind == "source_review_flags":
        if "needs_source_review" in filtered.columns:
            return flag_series(filtered["needs_source_review"])

    elif kind == "salary_over_threshold":
        if (
            "salary_minimum" in filtered.columns
            and "salary_maximum" in filtered.columns
        ):
            return (
                (filtered["salary_minimum"] > QUALITY_SALARY_THRESHOLD)
                | (filtered["salary_maximum"] > QUALITY_SALARY_THRESHOLD)
            )

    elif kind == "experience_over_threshold":
        if "minimum_years_experience" in filtered.columns:
            return (
                filtered["minimum_years_experience"]
                > QUALITY_EXPERIENCE_THRESHOLD
            )

    elif kind == "vacancies_over_threshold":
        if "number_of_vacancies" in filtered.columns:
            return (
                filtered["number_of_vacancies"]
                > QUALITY_VACANCY_THRESHOLD
            )

    elif kind == "vacancies_sentinel":
        if "number_of_vacancies" in filtered.columns:
            return (
                filtered["number_of_vacancies"]
                == QUALITY_SENTINEL_VACANCY
            )

    elif kind == "random_job_format":
        if "job_id_format" in filtered.columns:
            return (
                filtered["job_id_format"]
                .astype(str)
                .eq("RANDOM_JOB")
            )

    return empty


def outlier_measures(filtered):
    """
    The Team 6 review-rule table: area, rule text and matching row count.

    The 999 and RANDOM_JOB counts are reused from the same helpers that
    feed the metric cards, so the table and the cards can never disagree.
    """
    rows = []

    if "salary_minimum" in filtered.columns:
        for threshold in SALARY_REVIEW_THRESHOLDS:
            rows.append(
                {
                    "Area": "Salary",
                    "Review rule": f"salary_minimum > S${threshold:,}",
                    "Matching rows": int(
                        (filtered["salary_minimum"] > threshold).sum()
                    ),
                }
            )

    if "minimum_years_experience" in filtered.columns:
        for threshold in EXPERIENCE_REVIEW_THRESHOLDS:
            rows.append(
                {
                    "Area": "Experience",
                    "Review rule": (
                        f"minimum experience > {threshold} years"
                    ),
                    "Matching rows": int(
                        (
                            filtered["minimum_years_experience"]
                            > threshold
                        ).sum()
                    ),
                }
            )

    if "number_of_vacancies" in filtered.columns:
        for threshold in VACANCY_REVIEW_THRESHOLDS:
            rows.append(
                {
                    "Area": "Vacancies",
                    "Review rule": f"vacancies > {threshold}",
                    "Matching rows": int(
                        (
                            filtered["number_of_vacancies"]
                            > threshold
                        ).sum()
                    ),
                }
            )

        rows.append(
            {
                "Area": "Vacancies",
                "Review rule": f"vacancies = {QUALITY_SENTINEL_VACANCY}",
                "Matching rows": vacancy_sentinel_count(filtered),
            }
        )

    if "job_id_format" in filtered.columns:
        rows.append(
            {
                "Area": "Job ID",
                "Review rule": "RANDOM_JOB format",
                "Matching rows": random_job_count(filtered),
            }
        )

    return rows


def flagged_records(filtered, mask):
    """
    The review table: the first FLAGGED_RECORD_LIMIT matching rows, in
    the filtered frame's own order, plus the true matching total so the
    caption can report both.
    """
    columns = [
        column
        for column in FLAGGED_RECORD_COLUMNS
        if column in filtered.columns
    ]

    records = filtered.loc[mask, columns].head(FLAGGED_RECORD_LIMIT)

    return {
        "columns": columns,
        "total_matching": int(mask.sum()),
        "rows_shown": len(records),
        "cap": FLAGGED_RECORD_LIMIT,
        "data": [
            {
                column: json_value(record[column])
                for column in columns
            }
            for record in records.to_dict(orient="records")
        ],
    }


def calculate_data_quality_analysis(selections=None, review_population=None):
    """
    Datasets for the Data Quality & Outliers tab, from one filtered frame
    so the metric cards, the rule table and the review table always
    describe the same rows.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    population_spec = resolve_review_population(review_population)

    mask = review_population_mask(filtered, population_spec["kind"])

    rows_needing_source_review = (
        int(flag_series(filtered["needs_source_review"]).sum())
        if "needs_source_review" in filtered.columns
        else 0
    )

    return {
        "meta": {
            "endpoint": "/api/data-quality/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
            "review_population": population_spec["value"],
            "review_populations": [
                spec["value"]
                for spec in QUALITY_REVIEW_POPULATIONS
            ],
            "kpi_denominator": "rows_filtered (all filtered rows)",
            "flagged_record_cap": FLAGGED_RECORD_LIMIT,
            # app_deploy.py computes the issue rate once and reuses it in
            # the DAX expander and on this tab, so it is not recomputed
            # here. The frontend reads it from the overview payload.
            "issue_rate_source": (
                "/api/overview -> dax_measures."
                "data_quality_issue_rate"
            ),
        },
        "kpis": {
            "rows_needing_source_review": rows_needing_source_review,
            "vacancy_999_records": vacancy_sentinel_count(filtered),
            "random_job_records": random_job_count(filtered),
        },
        "outlier_measures": outlier_measures(filtered),
        "flagged_records": flagged_records(filtered, mask),
    }


# ============================================================
# REPOST ANALYSIS AGGREGATIONS
# ============================================================
# The Repost Analysis tab in app_deploy.py: three metric cards, a
# Posting Status count chart and a salary-by-posting-status table.
#
# UNITS (EXPLICIT)
# ----------------
# Every count here is a JOB ROW, not a distinct job_post_id. The main
# table can hold more than one row per job, so "Reposted Rows" is not
# the number of reposted jobs. The reference labels these "Rows" and
# this keeps that wording; use /api/overview's Unique Job Postings
# measure when a distinct count is needed.
#
# Repost Rate is reposted rows / total filtered rows, and it is NOT
# recomputed here: app_deploy.py computes it once at module level and
# reuses it in the DAX expander and on this tab, so the frontend reads
# it from the overview payload (see meta.repost_rate_source).
#
# ORDERING (DELIBERATE, TWO DIFFERENT RULES)
# -----------------------------------------
# The chart is built from value_counts(), so its rows are ordered by
# descending Jobs and the chart declares no sort.
# The table is built from groupby(), which sorts its keys ascending, so
# its rows read "Not Reposted", "Reposted".
# Both orders are inherited from the reference; neither is "corrected".

REPOST_STATUS_LABELS = {
    True: "Reposted",
    False: "Not Reposted",
}


def posting_status_series(filtered):
    """
    is_reposted as the two display labels, after the reference's
    fillna(False).astype(bool) coercion.
    """
    return flag_series(filtered["is_reposted"]).map(REPOST_STATUS_LABELS)


def reposted_row_count(filtered):
    """Reposted job rows. Feeds the first card and the non-reposted one."""
    if "is_reposted" not in filtered.columns:
        return 0

    return int(flag_series(filtered["is_reposted"]).sum())


def posting_status_chart(filtered):
    """
    Jobs by Posting Status - the two bar counts.

    Rows come back in value_counts order (descending by Jobs) and the
    reference chart sets no axis sort, so that order is the bar order.
    """
    if "is_reposted" not in filtered.columns:
        return {"available": False, "data": []}

    summary = (
        posting_status_series(filtered)
        .value_counts()
        .rename_axis("Posting Status")
        .reset_index(name="Jobs")
    )

    return {
        "available": True,
        "data": [
            {
                "Posting Status": str(record["Posting Status"]),
                "Jobs": json_number(record["Jobs"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def salary_by_posting_status(filtered):
    """
    Salary summary per posting status.

    NOTE: Jobs is the group size, so it counts every row in the status
    including rows with no salary, while Average/Median Salary skip
    them. Jobs can therefore exceed the salary-bearing row count; that
    is the reference's measure and is left alone.
    """
    if (
        "is_reposted" not in filtered.columns
        or "salary_midpoint" not in filtered.columns
    ):
        return {"available": False, "data": []}

    summary = (
        filtered.assign(
            posting_status=posting_status_series(filtered)
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

    return {
        "available": True,
        "data": [
            {
                "Posting Status": str(record["Posting Status"]),
                "Jobs": json_number(record["Jobs"]),
                "Average Salary": as_ratio(record["Average Salary"]),
                "Median Salary": as_ratio(record["Median Salary"]),
            }
            for record in summary.to_dict(orient="records")
        ],
    }


def calculate_repost_analysis(selections=None):
    """
    Datasets for the Repost Analysis tab, from one filtered frame so the
    cards, the chart and the table always agree.
    """
    context = load_overview_context()

    selections = selections or {}

    filtered = apply_filters(context, selections)

    reposted_rows = reposted_row_count(filtered)

    return {
        "meta": {
            "endpoint": "/api/repost/analysis",
            "source": "api",
            "filter_context": describe_selections(selections),
            "active_filters": selections,
            "filters_applied": len(selections),
            "rows_total": len(context["df"]),
            "rows_filtered": len(filtered),
            "count_unit": (
                "job rows (not distinct job_post_id values)"
            ),
            "repost_rate_source": (
                "/api/overview -> dax_measures.repost_rate"
            ),
        },
        "kpis": {
            "reposted_rows": reposted_rows,
            "total_rows": len(filtered),
            "non_reposted_rows": len(filtered) - reposted_rows,
        },
        "posting_status_counts": posting_status_chart(filtered),
        "salary_by_posting_status": salary_by_posting_status(filtered),
    }


# ============================================================
# DETAIL DRILLTHROUGH (ROW-LEVEL LOOKUP)
# ============================================================
# The Detail Drillthrough tab in app_deploy.py: a window on the filtered
# job rows, a job-id selector, one selected job's detail block, and that
# job's bridge rows.
#
# THIS IS A LOOKUP ENDPOINT, NOT AN AGGREGATE ENDPOINT
# ---------------------------------------------------
# The tab is inherently row-level, so unlike every other endpoint these
# return records. Three things keep the payload bounded:
#   * the record list is paginated (limit/offset) with a hard cap;
#   * the job-id selector list is capped;
#   * the bridge lookups are capped per job.
# The frontend never receives the filtered dataframe.
#
# DUPLICATE JOB IDS
# -----------------
# The reference does not deduplicate anywhere in this tab and neither
# does this module:
#   * the selector list is dropna().astype(str).head(10000), so a job id
#     appearing in several rows is offered several times;
#   * the detail lookup returns the FIRST matching row (.head(1)).
# `unique_in_window` is reported per response so the duplication is
# visible without changing the behaviour.
#
# BRIDGE LOOKUPS IGNORE THE SIDEBAR FILTERS
# -----------------------------------------
# The reference matches the selected id against the full bridge tables
# with exact string equality, so these two endpoints take no filter
# parameters: a job's full multi-label history is shown even if the
# active filter excluded some of its rows.

JOB_DISPLAY_COLUMNS = (
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
)

# The reference's "Rows to display" options and its default (index=2).
JOB_PAGE_LIMIT_CAP = 500
JOB_PAGE_LIMIT_DEFAULT = 100
JOB_OFFSET_CAP = 50_000

# The reference caps its job-id selector at 10,000 entries.
JOB_ID_LIMIT_CAP = 10_000

# Bridge rows for one job. A job with more labels than this is truncated
# and total_matching still reports the true size.
JOB_BRIDGE_ROW_CAP = int(os.getenv("SGJOBS_JOB_BRIDGE_ROW_CAP", "500"))


def display_columns_available(filtered):
    """The reference's display_columns, in its order."""
    return [
        column
        for column in JOB_DISPLAY_COLUMNS
        if column in filtered.columns
    ]


def records_to_rows(frame, columns):
    """A small DataFrame slice -> JSON-safe list of dicts."""
    return [
        {
            column: json_value(record[column])
            for column in columns
        }
        for record in frame.to_dict(orient="records")
    ]


def drillthrough_meta(context, filtered, selections, endpoint):
    return {
        "endpoint": endpoint,
        "source": "api",
        "filter_context": describe_selections(selections),
        "active_filters": selections,
        "filters_applied": len(selections),
        "rows_total": len(context["df"]),
        "rows_filtered": len(filtered),
    }


def job_records(context, selections, limit, offset):
    """
    One page of the filtered job rows, in the frame's own order.
    """
    filtered = apply_filters(context, selections)

    columns = display_columns_available(filtered)

    page = filtered.iloc[offset : offset + limit]

    return {
        "meta": {
            **drillthrough_meta(
                context,
                filtered,
                selections,
                "/api/jobs",
            ),
            "limit": limit,
            "offset": offset,
            "returned": len(page),
            "next_offset": (
                offset + limit
                if offset + len(page) < len(filtered)
                else None
            ),
            "has_more": offset + len(page) < len(filtered),
            "row_order": "filtered frame order (no sorting)",
        },
        "columns": columns,
        "rows": records_to_rows(page, columns),
    }


def job_id_list(context, selections, limit):
    """
    The job-id selector options: the first `limit` ids of the filtered
    frame, dropna + string, duplicates kept exactly as the reference
    keeps them.
    """
    filtered = apply_filters(context, selections)

    available = (
        "metadata_job_post_id" in filtered.columns
        and not filtered.empty
    )

    if not available:
        return {
            "meta": {
                **drillthrough_meta(
                    context,
                    filtered,
                    selections,
                    "/api/jobs/ids",
                ),
                "available": False,
                "limit": limit,
                "returned": 0,
                "unique_in_window": 0,
                "duplicates_kept": 0,
            },
            "job_ids": [],
        }

    job_ids = (
        filtered["metadata_job_post_id"]
        .dropna()
        .astype(str)
        .head(limit)
        .tolist()
    )

    unique_in_window = len(set(job_ids))

    return {
        "meta": {
            **drillthrough_meta(
                context,
                filtered,
                selections,
                "/api/jobs/ids",
            ),
            "available": True,
            "limit": limit,
            "returned": len(job_ids),
            "unique_in_window": unique_in_window,
            "duplicates_kept": len(job_ids) - unique_in_window,
        },
        "job_ids": job_ids,
    }


def job_detail(context, selections, job_post_id):
    """
    The first filtered row for one job id, or found=false.

    found=false is a normal answer, not an error: the reference renders
    nothing when the id is no longer in the filtered frame, which happens
    as soon as the user changes a filter.
    """
    filtered = apply_filters(context, selections)

    columns = display_columns_available(filtered)

    base_meta = drillthrough_meta(
        context,
        filtered,
        selections,
        "/api/jobs/{job_post_id}",
    )

    metrics = {
        "salary_midpoint": None,
        "number_of_vacancies": None,
        "applications_per_vacancy": None,
        "opportunity_score": None,
    }

    if (
        "metadata_job_post_id" not in filtered.columns
        or filtered.empty
    ):
        return {
            "meta": {
                **base_meta,
                "job_post_id": job_post_id,
                "found": False,
                "reason": "no job id column or no filtered rows",
            },
            "record": None,
            "metrics": metrics,
        }

    match = filtered[
        filtered["metadata_job_post_id"]
        .astype(str)
        .eq(job_post_id)
    ]

    if match.empty:
        return {
            "meta": {
                **base_meta,
                "job_post_id": job_post_id,
                "found": False,
                "reason": "not present in the current filter context",
                "matching_rows": 0,
            },
            "record": None,
            "metrics": metrics,
        }

    record = match[columns].head(1)

    matching_rows = int(
        filtered["metadata_job_post_id"]
        .astype(str)
        .eq(job_post_id)
        .sum()
    )

    for key in metrics:
        if key in record.columns:
            metrics[key] = json_value(record.iloc[0][key])

    return {
        "meta": {
            **base_meta,
            "job_post_id": job_post_id,
            "found": True,
            # Duplicates are kept by the reference; the first row wins.
            "matching_rows": matching_rows,
            "row_selection": "first matching row (.head(1))",
        },
        "record": records_to_rows(record, columns)[0],
        "metrics": metrics,
    }


def job_bridge_rows(context, job_post_id, bridge_key, name_column, label):
    """
    One job's bridge rows, matched on exact job_post_id strings.

    No sidebar filters are applied, matching the reference.
    """
    frame = context[bridge_key]

    bridge_meta = {
        "source": "api",
        "endpoint": label,
        "job_post_id": job_post_id,
        "bridge": bridge_key,
        "bridge_rows": len(frame),
        "cap": JOB_BRIDGE_ROW_CAP,
    }

    columns = [
        column
        for column in ("job_post_id", name_column)
        if column in frame.columns
    ]

    if not columns:
        return {
            "meta": {**bridge_meta, "returned": 0, "total_matching": 0},
            "columns": [],
            "rows": [],
        }

    matches = frame[
        frame["job_post_id"]
        .astype(str)
        .eq(job_post_id)
    ]

    page = matches.head(JOB_BRIDGE_ROW_CAP)

    return {
        "meta": {
            **bridge_meta,
            "returned": len(page),
            "total_matching": int(len(matches)),
            "truncated": len(page) < len(matches),
        },
        "columns": columns,
        "rows": records_to_rows(page, columns),
    }


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="SGJobs API",
    description=(
        "Decoupled practice backend. Owns the data loading, the sidebar "
        "filter definitions and the Overview KPI calculations; the "
        "Streamlit frontend only collects selections and renders the JSON "
        "returned here."
    ),
    version="0.9.0",
)

# No CORS middleware on purpose: the Streamlit process calls this API
# server-to-server with `requests`, so the browser never talks to it
# directly. CORS only becomes relevant if a JS frontend is added.


@app.get("/api/health")
def health():
    """Cheap check the frontend uses to tell 'server down' from 'bad data'."""
    return {
        "status": "ok",
        "data_loaded": load_overview_context.cache_info().currsize > 0,
    }


@app.get("/api/filters")
def get_filters():
    """
    Sidebar metadata: label, state key, availability and option list for
    each filter, in the order app_deploy.py renders them.

    The frontend renders these descriptors as-is, so the option ordering
    rules stay in one place.
    """
    try:
        descriptors = get_filter_descriptors()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return {
        "filters": descriptors,
        "meta": {
            "endpoint": "/api/filters",
            "count": len(descriptors),
        },
    }


def parse_overview_filters(
    employment_types: List[str] = Query(default_factory=list),
    category_primary: List[str] = Query(default_factory=list),
    category_bridge: List[str] = Query(default_factory=list),
    skill_bridge: List[str] = Query(default_factory=list),
    seniority_group: List[str] = Query(default_factory=list),
    experience_band: List[str] = Query(default_factory=list),
    vacancy_band: List[str] = Query(default_factory=list),
    salary_band: List[str] = Query(default_factory=list),
    opportunity_band: List[str] = Query(default_factory=list),
    posting_year: List[int] = Query(default_factory=list),
) -> Dict[str, List[Any]]:
    """
    Shared query-parameter parsing + validation for the Overview
    endpoints. Repeat a parameter once per selected value, e.g.
        /api/overview?salary_band=5K%E2%80%937K&posting_year=2025&posting_year=2026
    """
    raw_selections = {
        "employment_types": employment_types,
        "category_primary": category_primary,
        "category_bridge": category_bridge,
        "skill_bridge": skill_bridge,
        "seniority_group": seniority_group,
        "experience_band": experience_band,
        "vacancy_band": vacancy_band,
        "salary_band": salary_band,
        "opportunity_band": opportunity_band,
        "posting_year": posting_year,
    }

    try:
        context = load_overview_context()
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    return validate_selections(context, raw_selections)


@app.get("/api/overview")
def get_overview(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Overview KPIs for the current filter selection.
    """
    return calculate_overview_kpis(selections)


@app.get("/api/overview/charts")
def get_overview_charts(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Pre-aggregated datasets for the four Overview charts, for the same
    filter selection. Nothing larger than a few hundred rows is
    returned: the frontend never sees the raw records.
    """
    return calculate_overview_charts(selections)


@app.get("/api/salary/analysis")
def get_salary_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Datasets for the Salary Analysis tab: salary band counts, average
    salary by job function, and the five salary summary measures.

    Same filter parameters as /api/overview.
    """
    return calculate_salary_analysis(selections)


@app.get("/api/opportunity/analysis")
def get_opportunity_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Datasets for the Opportunity Analysis tab: opportunity band counts
    and the top 15 job functions by average opportunity score.

    The ranking decision (sample-size floor, whether the fallback to all
    job functions was used) is returned alongside the rows so the
    frontend can show the reference caption for that branch.

    Same filter parameters as /api/overview.
    """
    return calculate_opportunity_analysis(selections)


@app.get("/api/demand/analysis")
def get_demand_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Datasets for the Demand & Seniority tab: seniority counts, average
    and median salary by seniority, and the capped, seeded scatter
    sample.

    The scatter payload is row-level by necessity (a scatter plot cannot
    be drawn from aggregates) and is capped at
    meta.scatter_sample_limit rows.

    Same filter parameters as /api/overview.
    """
    return calculate_demand_analysis(selections)


@app.get("/api/skills-categories/analysis")
def get_skills_categories_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Datasets for the Skills & Categories tab: top 15 official Job
    Functions and top 15 skills, each counted as distinct job postings.

    Bridge rows are filtered by job_post_id in the backend; the full
    bridge tables are never returned.

    Same filter parameters as /api/overview.
    """
    return calculate_skills_categories_analysis(selections)


@app.get("/api/data-quality/analysis")
def get_data_quality_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
    review_population: Optional[str] = Query(default=None),
):
    """
    Datasets for the Data Quality & Outliers tab.

    Returns the three metric-card counts, the Team 6 review-rule table,
    and up to meta.flagged_record_cap review rows for the selected
    review population. Pass review_population=<label> to change it; the
    accepted labels are listed in meta.review_populations and the first
    one is the default.

    Data Quality Issue Rate is not repeated here: app_deploy.py computes
    it once and reuses it, so the frontend reads it from /api/overview
    (see meta.issue_rate_source).

    Same filter parameters as /api/overview.
    """
    return calculate_data_quality_analysis(selections, review_population)


@app.get("/api/repost/analysis")
def get_repost_analysis(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    Datasets for the Repost Analysis tab: reposted/non-reposted job-row
    counts, Posting Status counts and salary by posting status.

    Repost Rate is not repeated here: app_deploy.py computes it once and
    reuses it, so the frontend reads it from /api/overview (see
    meta.repost_rate_source).

    Counts are job rows, not distinct job_post_id values.

    Same filter parameters as /api/overview.
    """
    return calculate_repost_analysis(selections)


# --------------------------------------------------------
# DETAIL DRILLTHROUGH
# --------------------------------------------------------
# Route order matters: /api/jobs/ids must be declared before
# /api/jobs/{job_post_id}, otherwise "ids" would be swallowed by the
# path parameter.

@app.get("/api/jobs")
def get_jobs(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
    limit: int = Query(
        default=JOB_PAGE_LIMIT_DEFAULT,
        ge=1,
        le=JOB_PAGE_LIMIT_CAP,
    ),
    offset: int = Query(default=0, ge=0, le=JOB_OFFSET_CAP),
):
    """
    One page of matching job records, in the filtered frame's own order
    (never sorted).

    limit defaults to 100 and is capped at 500; offset defaults to 0.
    meta.next_offset is null on the last page.
    """
    return job_records(
        load_overview_context(),
        selections,
        limit,
        offset,
    )


@app.get("/api/jobs/ids")
def get_job_ids(
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
    limit: int = Query(
        default=JOB_ID_LIMIT_CAP,
        ge=1,
        le=JOB_ID_LIMIT_CAP,
    ),
):
    """
    Job-id selector options: the first `limit` ids of the filtered frame.

    Duplicate ids are kept, exactly as the reference keeps them.
    meta.unique_in_window and meta.duplicates_kept report how many.
    """
    return job_id_list(
        load_overview_context(),
        selections,
        limit,
    )


@app.get("/api/jobs/{job_post_id}")
def get_job_detail(
    job_post_id: str,
    selections: Dict[str, List[Any]] = Depends(parse_overview_filters),
):
    """
    One job's detail record: the FIRST filtered row carrying this
    job_post_id, plus the four drillthrough metric values.

    Returns meta.found=false (HTTP 200) when the id is not in the
    current filter context, which is what the reference renders as an
    empty detail block.
    """
    return job_detail(
        load_overview_context(),
        selections,
        job_post_id,
    )


@app.get("/api/jobs/{job_post_id}/categories")
def get_job_categories(job_post_id: str):
    """
    One job's category-bridge rows, matched on exact job_post_id.

    Deliberately takes no filter parameters: the reference matches the
    full category bridge, not the filtered subset.
    """
    return job_bridge_rows(
        load_overview_context(),
        job_post_id,
        "category_bridge",
        "category_name",
        "/api/jobs/{job_post_id}/categories",
    )


@app.get("/api/jobs/{job_post_id}/skills")
def get_job_skills(job_post_id: str):
    """
    One job's skill-bridge rows, matched on exact job_post_id.

    Deliberately takes no filter parameters, for the same reason.
    """
    return job_bridge_rows(
        load_overview_context(),
        job_post_id,
        "skill_bridge",
        "skill_name",
        "/api/jobs/{job_post_id}/skills",
    )