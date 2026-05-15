# KS5 GCE A Level Subject Results Explorer

Interactive tool for exploring the provided KS5 Excel file by school, subject, grade, and local authority filters.

## What it does

- Loads data from `Copy of 2024-2025_england_ks5underlying by A level subjects only.xlsx`
- Builds a local SQLite database at `/tmp/ks5_subject_results.db` (Streamlit Community Cloud-safe)
- Provides filter controls for:
  - School
  - Subject
  - Grade / total entries
  - Local authority
  - Single "Clear all selected filters" action
- Shows:
  - Top-line metrics
  - A per-school subject-grade matrix
  - A school comparison table (totals, pass/fail counts, pass/fail rates, A*-B metrics)
  - CSV downloads for the grade matrix and school comparison table
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
