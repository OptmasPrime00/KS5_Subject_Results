from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

from data_loader import ensure_database_is_fresh

REPO_ROOT = Path(__file__).resolve().parent
EXCEL_PATH = REPO_ROOT / "Copy of 2024-2025_england_ks5underlying by A level subjects only.xlsx"
DB_PATH = Path("/tmp") / "ks5_subject_results.db"

FILTERS: list[tuple[str, str]] = [
    ("school_name", "School"),
    ("subject", "Subject"),
    ("grade_or_total_entries", "Grade / Total entries"),
    ("local_authority", "Local authority"),
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


def get_filter_key(column: str) -> str:
    return f"filter_{column}"


def _to_int_series(series: pd.Series) -> pd.Series:
    return series.round(0).astype(int)


def apply_multiselect_filter(df: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    options = sorted(v for v in df[column].dropna().unique().tolist() if str(v).strip())
    key = get_filter_key(column)
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
        for column, _ in FILTERS:
            st.session_state[get_filter_key(column)] = []
        st.rerun()

    filtered = df.copy()
    for column, label in FILTERS:
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
            ["school_name", "subject", "grade_display"],
            as_index=False,
            dropna=False,
        )["grade_count"]
        .sum()
        .pivot_table(
            index=["school_name", "subject"],
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

    id_columns = ["school_name", "subject"]
    ordered_grades = _order_grade_columns([column for column in pivot.columns if column not in id_columns])
    pivot = pivot[id_columns + ordered_grades].sort_values(id_columns).reset_index(drop=True)

    for grade in ordered_grades:
        pivot[grade] = _to_int_series(pivot[grade])

    return pivot


def build_school_comparison_table(filtered: pd.DataFrame) -> pd.DataFrame:
    grade_data = filtered.copy()
    grade_data["grade_display"] = grade_data["grade_or_total_entries"].replace(GRADE_RENAMES)
    grade_data["grade_count"] = grade_data["number_of_exams"].fillna(0)

    comparison = (
        grade_data.groupby(["school_name", "grade_display"], as_index=False)["grade_count"]
        .sum()
        .pivot_table(
            index=["school_name"],
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

    comparison.loc[:, "total_exams"] = _to_int_series(comparison["Total"])
    comparison.loc[:, "fail_exams"] = _to_int_series(comparison["Fail"])
    comparison.loc[:, "pass_exams"] = (comparison["total_exams"] - comparison["fail_exams"]).clip(lower=0)
    comparison.loc[:, "a_star_to_b_exams"] = _to_int_series(comparison["A*"] + comparison["A"] + comparison["B"])
    comparison.loc[:, "pass_rate_%"] = (
        comparison["pass_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)
    comparison.loc[:, "fail_rate_%"] = (
        comparison["fail_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)
    comparison.loc[:, "a_star_to_b_rate_%"] = (
        comparison["a_star_to_b_exams"].div(comparison["total_exams"]).where(comparison["total_exams"] > 0) * 100
    ).round(1)

    comparison = comparison.sort_values(
        ["total_exams", "pass_rate_%", "school_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    comparison_columns = [
        "school_name",
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
    id_columns = ["school_name", "subject"]
    if show_all_grades:
        return grade_breakdown_table

    preferred = [grade for grade in PREFERRED_GRADE_ORDER if grade in grade_breakdown_table.columns]
    return grade_breakdown_table[id_columns + preferred]


def main() -> None:
    st.set_page_config(page_title="KS5 GCE A Level Subject Results Explorer", layout="wide")
    st.title("KS5 GCE A Level Subject Results Explorer")

    if not EXCEL_PATH.exists():
        st.error(f"Excel file not found: {EXCEL_PATH}")
        st.stop()

    ensure_database_is_fresh(excel_path=EXCEL_PATH, sqlite_path=DB_PATH)
    df = read_results(DB_PATH)

    filtered = render_filters(df)
    grade_breakdown_table = build_school_subject_grade_table(filtered)
    school_comparison_table = build_school_comparison_table(filtered)

    st.subheader("Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Filtered rows", f"{len(filtered):,}")
    col2.metric("Schools", filtered["school_name"].nunique())
    col3.metric("Subjects", filtered["subject"].nunique())
    col4.metric(
        "Total numeric exams",
        f"{filtered['number_of_exams'].fillna(0).sum():,.0f}",
    )

    st.subheader("Per-school subject grade breakdown")
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
