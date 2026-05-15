from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import ensure_database_is_fresh

REPO_ROOT = Path(__file__).resolve().parent
EXCEL_PATH = REPO_ROOT / "Copy of 2024-2025_england_ks5underlying Kingston Surrey Sutton institution subject.xlsx"
DB_PATH = REPO_ROOT / "data" / "ks5_subject_results.db"

FILTER_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Main filters",
        [
            ("school_name", "School"),
            ("qualification", "Qualification"),
            ("subject", "Subject"),
        ],
    ),
    (
        "Additional filters",
        [
            ("grade_or_total_entries", "Grade / Total entries"),
            ("local_authority", "Local authority"),
            ("exam_cohort", "Exam cohort"),
        ],
    ),
]

GRADE_RENAMES = {
    "*": "A*",
}

PREFERRED_GRADE_ORDER = ["A*", "A", "B", "C", "D", "E", "Fail", "Total"]


@st.cache_data(show_spinner=False)
def read_results(sqlite_path: Path) -> pd.DataFrame:
    with sqlite3.connect(sqlite_path) as conn:
        df = pd.read_sql_query("SELECT * FROM institution_subject_results", conn)
    return df


def apply_multiselect_filter(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    options = sorted(v for v in df[column].dropna().unique().tolist() if str(v).strip())
    key = f"filter_{column}"
    selected = st.sidebar.multiselect(
        label,
        options=options,
        default=[],
        key=key,
        placeholder=f"Type to search {label.lower()}",
    )
    if selected:
        return df[df[column].isin(selected)]
    return df


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filters")
    if st.sidebar.button("Clear all selected filters", use_container_width=True):
        for _, grouped_filters in FILTER_GROUPS:
            for column, _ in grouped_filters:
                st.session_state[f"filter_{column}"] = []
        st.rerun()

    filtered = df.copy()
    for group_label, grouped_filters in FILTER_GROUPS:
        with st.sidebar.expander(group_label, expanded=True):
            for column, label in grouped_filters:
                filtered = apply_multiselect_filter(filtered, column, label)
    return filtered


def _order_grade_columns(columns: list[str]) -> list[str]:
    preferred = [grade for grade in PREFERRED_GRADE_ORDER if grade in columns]
    remaining = sorted(column for column in columns if column not in preferred)
    return preferred + remaining


def build_school_subject_grade_table(filtered: pd.DataFrame) -> pd.DataFrame:
    grade_data = filtered.copy()
    grade_data["grade_display"] = grade_data["grade_or_total_entries"].replace(GRADE_RENAMES)
    grade_data["grade_count"] = grade_data["number_of_exams"].fillna(0)

    pivot = (
        grade_data.groupby(
            ["school_name", "qualification", "subject", "grade_display"],
            as_index=False,
            dropna=False,
        )["grade_count"]
        .sum()
        .pivot_table(
            index=["school_name", "qualification", "subject"],
            columns="grade_display",
            values="grade_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    for grade in PREFERRED_GRADE_ORDER:
        if grade not in pivot.columns:
            pivot[grade] = 0

    id_columns = ["school_name", "qualification", "subject"]
    ordered_grades = _order_grade_columns([column for column in pivot.columns if column not in id_columns])
    pivot = pivot[id_columns + ordered_grades].sort_values(id_columns).reset_index(drop=True)

    for grade in ordered_grades:
        pivot[grade] = pivot[grade].round(0).astype(int)

    return pivot


def build_school_comparison_table(filtered: pd.DataFrame) -> pd.DataFrame:
    grade_data = filtered.copy()
    grade_data["grade_display"] = grade_data["grade_or_total_entries"].replace(GRADE_RENAMES)
    grade_data["grade_count"] = grade_data["number_of_exams"].fillna(0)

    comparison = (
        grade_data.groupby(["school_name", "qualification", "grade_display"], as_index=False)["grade_count"]
        .sum()
        .pivot_table(
            index=["school_name", "qualification"],
            columns="grade_display",
            values="grade_count",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )

    for grade in ["Total", "Fail", "A*", "A", "B"]:
        if grade not in comparison.columns:
            comparison[grade] = 0

    comparison["total_exams"] = comparison["Total"].round(0).astype(int)
    comparison["fail_exams"] = comparison["Fail"].round(0).astype(int)
    comparison["pass_exams"] = (comparison["total_exams"] - comparison["fail_exams"]).clip(lower=0)
    comparison["a_star_to_b_exams"] = (
        comparison["A*"].fillna(0) + comparison["A"].fillna(0) + comparison["B"].fillna(0)
    ).round(0).astype(int)
    comparison["pass_rate_%"] = (
        comparison["pass_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)
    comparison["fail_rate_%"] = (
        comparison["fail_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)
    comparison["a_star_to_b_rate_%"] = (
        comparison["a_star_to_b_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)

    comparison = comparison.sort_values(
        ["total_exams", "pass_rate_%", "school_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    comparison_columns = [
        "school_name",
        "qualification",
        "total_exams",
        "fail_exams",
        "pass_exams",
        "pass_rate_%",
        "fail_rate_%",
        "a_star_to_b_exams",
        "a_star_to_b_rate_%",
    ]
    return comparison[comparison_columns]


def select_grade_breakdown_columns(grade_breakdown_table: pd.DataFrame, show_all_grades: bool) -> pd.DataFrame:
    id_columns = ["school_name", "qualification", "subject"]
    if show_all_grades:
        return grade_breakdown_table

    preferred = [grade for grade in PREFERRED_GRADE_ORDER if grade in grade_breakdown_table.columns]
    return grade_breakdown_table[id_columns + preferred]


def main() -> None:
    st.set_page_config(page_title="KS5 Subject Results Explorer", layout="wide")
    st.title("KS5 Subject Results Explorer")
    st.caption("Filter school-level KS5 subject outcomes from the provided Excel file.")

    if not EXCEL_PATH.exists():
        st.error(f"Excel file not found: {EXCEL_PATH}")
        st.stop()

    ensure_database_is_fresh(excel_path=EXCEL_PATH, sqlite_path=DB_PATH)
    df = read_results(DB_PATH)

    filtered = render_filters(df)
    grade_breakdown_table = build_school_subject_grade_table(filtered)
    school_comparison_table = build_school_comparison_table(filtered)

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

    st.subheader("Per-school subject grade breakdown")
    st.caption("Rows are subjects; columns are grades, including Fail and Total.")
    show_all_grades = st.toggle("Show all grade columns", value=False)
    visible_grade_breakdown_table = select_grade_breakdown_columns(grade_breakdown_table, show_all_grades)
    st.dataframe(visible_grade_breakdown_table, use_container_width=True, hide_index=True)
    st.download_button(
        "Download grade breakdown as CSV",
        data=grade_breakdown_table.to_csv(index=False).encode("utf-8"),
        file_name="ks5_school_subject_grade_breakdown.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.subheader("School comparison")
    st.caption("Compare schools by total entries, pass/fail counts, and key rates.")
    st.dataframe(school_comparison_table, use_container_width=True, hide_index=True)
    comparison_chart_data = school_comparison_table.copy()
    comparison_chart_data["school_label"] = (
        comparison_chart_data["school_name"] + " | " + comparison_chart_data["qualification"]
    )
    st.bar_chart(comparison_chart_data.set_index("school_label")["pass_rate_%"], height=320)
    st.download_button(
        "Download school comparison as CSV",
        data=school_comparison_table.to_csv(index=False).encode("utf-8"),
        file_name="ks5_school_comparison.csv",
        mime="text/csv",
        use_container_width=True,
    )

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
