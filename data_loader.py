from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SOURCE_SHEET = "Institution_subject_results"
TABLE_NAME = "institution_subject_results"
CREATE_SCHOOL_SUBJECT_INDEX_QUERY = (
    "CREATE INDEX IF NOT EXISTS idx_school_qualification_subject "
    "ON institution_subject_results(school_name, qualification, subject)"
)
CREATE_LOCAL_AUTHORITY_INDEX_QUERY = (
    "CREATE INDEX IF NOT EXISTS idx_local_authority ON institution_subject_results(local_authority)"
)
TABLE_ROW_COUNT_QUERY = "SELECT COUNT(*) FROM institution_subject_results"

COLUMN_RENAMES = {
    "Year": "year",
    "Local Authority": "local_authority",
    "URN": "urn",
    "School or college name": "school_name",
    "School or college type": "school_type",
    "Exam cohort": "exam_cohort",
    "Qualification": "qualification",
    "Level": "level",
    "ASIZE": "asize",
    "GSIZE": "gsize",
    "Grade structure": "grade_structure",
    "Subject": "subject",
    "Grade/Total entries": "grade_or_total_entries",
    "Number of exams": "number_of_exams_raw",
}


def load_excel_to_sqlite(excel_path: Path, sqlite_path: Path) -> None:
    """Load the KS5 subject results workbook into a SQLite database."""
    df = pd.read_excel(excel_path, sheet_name=SOURCE_SHEET).rename(columns=COLUMN_RENAMES).copy()

    # Normalize text columns for cleaner filtering.
    text_columns = [
        "local_authority",
        "school_name",
        "school_type",
        "exam_cohort",
        "qualification",
        "grade_structure",
        "subject",
        "grade_or_total_entries",
        "number_of_exams_raw",
    ]
    for column in text_columns:
        if column in df.columns:
            df.loc[:, column] = df[column].fillna("Unknown").astype(str).str.strip()

    # Create numeric helper columns for metrics.
    numeric_columns = ["year", "urn", "level", "asize", "gsize"]
    for column in numeric_columns:
        if column in df.columns:
            df.loc[:, column] = pd.to_numeric(df[column], errors="coerce")

    df.loc[:, "number_of_exams"] = pd.to_numeric(df["number_of_exams_raw"], errors="coerce")

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as conn:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        conn.execute(CREATE_SCHOOL_SUBJECT_INDEX_QUERY)
        conn.execute(CREATE_LOCAL_AUTHORITY_INDEX_QUERY)
        conn.commit()


def _database_has_rows(sqlite_path: Path) -> bool:
    if not sqlite_path.exists():
        return False
    try:
        with sqlite3.connect(sqlite_path) as conn:
            result = conn.execute(
                "SELECT EXISTS(SELECT 1 FROM sqlite_master WHERE type='table' AND name=?)",
                (TABLE_NAME,),
            ).fetchone()
            if not result or result[0] == 0:
                return False
            row_count = conn.execute(TABLE_ROW_COUNT_QUERY).fetchone()
            return bool(row_count and row_count[0] > 0)
    except sqlite3.Error:
        return False


def ensure_database_is_fresh(excel_path: Path, sqlite_path: Path) -> None:
    """Rebuild the SQLite database if the source workbook changed or DB is missing."""
    should_rebuild = (
        (not sqlite_path.exists())
        or (sqlite_path.stat().st_mtime < excel_path.stat().st_mtime)
        or (not _database_has_rows(sqlite_path))
    )
    if should_rebuild:
        load_excel_to_sqlite(excel_path=excel_path, sqlite_path=sqlite_path)
