from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import ensure_database_is_fresh

REPO_ROOT = Path(__file__).resolve().parent
EXCEL_PATH = REPO_ROOT / "Copy of 2024-2025_england_ks5underlying Kingston Surrey Sutton institution subject.xlsx"
DB_PATH = REPO_ROOT / "data" / "ks5_subject_results.db"


@st.cache_data(show_spinner=False)
def read_results(sqlite_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as conn:
        df = pd.read_sql_query("SELECT * FROM institution_subject_results", conn)
    return df


def apply_multiselect_filter(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    options = sorted(v for v in df[column].dropna().unique().tolist() if str(v).strip())
    selected = st.sidebar.multiselect(label, options=options, default=options)
    if selected:
        return df[df[column].isin(selected)]
    return df.iloc[0:0]


def main() -> None:
    st.set_page_config(page_title="KS5 Subject Results Explorer", layout="wide")
    st.title("KS5 Subject Results Explorer")
    st.caption("Filter school-level KS5 subject outcomes from the provided Excel file.")

    if not EXCEL_PATH.exists():
        st.error(f"Excel file not found: {EXCEL_PATH}")
        st.stop()

    ensure_database_is_fresh(excel_path=EXCEL_PATH, sqlite_path=DB_PATH)
    df = read_results(DB_PATH)

    st.sidebar.header("Filters")
    filtered = df.copy()
    filtered = apply_multiselect_filter(filtered, "school_name", "School")
    filtered = apply_multiselect_filter(filtered, "qualification", "Qualification")
    filtered = apply_multiselect_filter(filtered, "subject", "Subject")
    filtered = apply_multiselect_filter(filtered, "grade_or_total_entries", "Grade / Total entries")
    filtered = apply_multiselect_filter(filtered, "local_authority", "Local authority")
    filtered = apply_multiselect_filter(filtered, "exam_cohort", "Exam cohort")

    st.subheader("Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Filtered rows", f"{len(filtered):,}")
    col2.metric("Schools", filtered["school_name"].nunique())
    col3.metric("Subjects", filtered["subject"].nunique())
    col4.metric("Qualifications", filtered["qualification"].nunique())
    col5.metric(
        "Total numeric exams",
        f"{filtered['number_of_exams'].fillna(0).sum():,.0f}",
    )

    st.subheader("Subject and grade table")
    summary_table = (
        filtered.groupby(
            ["school_name", "qualification", "subject", "grade_or_total_entries"],
            dropna=False,
            as_index=False,
        )
        .agg(
            total_numeric_exams=("number_of_exams", "sum"),
            avg_asize=("asize", "mean"),
            avg_gsize=("gsize", "mean"),
            rows=("subject", "count"),
        )
        .sort_values(["school_name", "qualification", "subject", "grade_or_total_entries"])
    )
    st.dataframe(summary_table, use_container_width=True, hide_index=True)

    st.subheader("Detailed rows")
    display_columns = [
        "year",
        "local_authority",
        "urn",
        "school_name",
        "school_type",
        "exam_cohort",
        "qualification",
        "level",
        "subject",
        "grade_or_total_entries",
        "number_of_exams_raw",
        "number_of_exams",
        "asize",
        "gsize",
    ]
    st.dataframe(filtered[display_columns], use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
