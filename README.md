# KS5 GCE A Level Subject Results Explorer

Interactive tool for exploring the KS5 subject results by school, subject, grade, and local authority filters.

## What it does

- Loads data from a local SQLite database at `data/ks5_subject_results.db`
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

The repository now expects `data/ks5_subject_results.db` to already exist.
