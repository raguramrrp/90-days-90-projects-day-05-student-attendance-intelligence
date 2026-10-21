# Data Specifications & Sample Spreadsheets

This directory contains data templates, schema specifications, and synthetic generation documentation for the **Student Attendance Intelligence & Early Warning System**.

---

## 1. File Manifest

- `sample_attendance_template.xlsx`: Standard institutional Microsoft Excel (.xlsx) template preformatted with header styling, data validation rules, and sample entries for batch attendance marking.
- `ml_models/`: Serialized scikit-learn Decision Tree model artifacts (`attendance_decision_tree.joblib`) and confusion matrix evaluations (`evaluation_metrics.json`).

---

## 2. Excel Import Schema

| Column Name | Expected Format | Required? | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| **Roll Number** | String (alphanumeric) | Yes | Unique student identifier | `23AI001` |
| **Student Name** | String | Optional | Student full name (for human verification) | `Aarav Sharma` |
| **Subject Code** | String (uppercase) | Yes | Valid course catalog code | `AI701` |
| **Date (YYYY-MM-DD)** | Date string | Yes | ISO 8601 date of lecture session | `2026-10-21` |
| **Period (1-8)** | Integer (1–8) | Yes | Timetable class period slot | `1` |
| **Status (PRESENT/ABSENT/EXCUSED)** | Enum string | Yes | Attendance state: `PRESENT`, `ABSENT`, or `EXCUSED` | `PRESENT` |
| **Remarks** | String | Optional | Context note (e.g., late bus, symposium OD) | `Late arrival` |

---

## 3. Synthetic Demo Dataset Schema

The `seed_demo_data` command synthesizes realistic academic attendance histories across a multi-week term:

- **Department:** `AIDS` (Artificial Intelligence & Data Science), `CSE` (Computer Science & Engineering)
- **Class Sections:** `AIDS-IV-A`, `AIDS-IV-B`
- **Courses:** `AI701` (Deep Learning), `AI702` (NLP & LLMs), `AI703` (Computer Vision), `CS704` (Cloud & MLOps), `AI705` (Reinforcement Learning)
- **Cohort Distribution:**
  - **Safe Students ($\ge 80\%$):** `23AI001` (92%), `23AI020` (84%), `23AI030` (100%)
  - **Warning Buffer ($75\% - 80\%$):** `23AI008` (77%), `23AI025` (79%)
  - **Critical Debarment Risk ($< 75\%$):** `23AI014` (68%)
- **Parental Links:** 1-to-1 and 1-to-many parent-child relations with notification preference profiles.
- **Workflow Artifacts:** Sample Leave & On-Duty applications, attendance correction disputes, and audit records.

---

## 4. Privacy & Ethical Standards

All synthetic student records, parental contact numbers, and email addresses in this dataset are strictly fictitious. No real personal student data or institutional records are stored or committed.
