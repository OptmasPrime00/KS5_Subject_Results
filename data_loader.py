from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SOURCE_SHEET = "Institution_subject_results"

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
    df = pd.read_excel(excel_path, sheet_name=SOURCE_SHEET)
    df = df.rename(columns=COLUMN_RENAMES)

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
        df[column] = df[column].fillna("Unknown").astype(str).str.strip()

    # Create numeric helper columns for metrics.
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["urn"] = pd.to_numeric(df["urn"], errors="coerce")
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    df["asize"] = pd.to_numeric(df["asize"], errors="coerce")
    df["gsize"] = pd.to_numeric(df["gsize"], errors="coerce")
    df["number_of_exams"] = pd.to_numeric(df["number_of_exams_raw"], errors="coerce")

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as conn:
        df.to_sql("institution_subject_results", conn, if_exists="replace", index=False)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_school_qualification_subject ON institution_subject_results(school_name, qualification, subject)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_local_authority ON institution_subject_results(local_authority)"
        )
        conn.commit()


def ensure_database_is_fresh(excel_path: Path, sqlite_path: Path) -> None:
    """Rebuild the SQLite database if the source workbook changed or DB is missing."""
    if (not sqlite_path.exists()) or (sqlite_path.stat().st_mtime < excel_path.stat().st_mtime):
        load_excel_to_sqlite(excel_path=excel_path, sqlite_path=sqlite_path)
