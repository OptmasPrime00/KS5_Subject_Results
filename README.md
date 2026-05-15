# KS5 Subject Results Explorer

Interactive tool for exploring the provided KS5 Excel file by school, qualification, subject, grade, and other filters.

## What it does

- Loads data from `Copy of 2024-2025_england_ks5underlying Kingston Surrey Sutton institution subject.xlsx`
- Builds a local SQLite database at `data/ks5_subject_results.db`
- Provides filter controls for:
  - School
  - Qualification
  - Subject
  - Grade / total entries
  - Local authority
  - Exam cohort
- Shows:
  - Top-line metrics
  - A grouped subject/grade table with useful metrics (total numeric exams, average ASIZE, average GSIZE)
  - Detailed filtered rows

## Setup

```bash
python -m pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Then open the local URL shown in your terminal (usually `http://localhost:8501`).
