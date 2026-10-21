# User Guide & Operations Manual

This guide walks through every role portal in the **Student Attendance Intelligence & Early Warning System**.

---

## 1. Quick Sign-In & 1-Click Demo Accounts

On the login page (`http://127.0.0.1:8000/login/`), convenient one-click buttons pre-fill demonstration accounts:

| Portal | Username | Password | Persona & Context |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | Institutional Admin (Full academic oversight) |
| **Faculty** | `prof_ananya` | `faculty123` | Dr. Ananya Sharma (Teaches AI701 & AI702) |
| **Student (Safe)** | `23ai001` | `student123` | Aarav Sharma (92% Attendance, Safe) |
| **Student (Warning)**| `23ai008` | `student123` | Diya Mehta (77% Attendance, Warning Buffer) |
| **Student (Critical)**| `23ai014` | `student123` | Rohan Verma (68% Attendance, Critical Debarment Risk) |
| **Parent** | `parent_sharma` | `parent123` | Mr. Rajesh Sharma (Father of Aarav Sharma) |

---

## 2. Administrator Portal Guide

### A. Executive Dashboard (`/admin-portal/`)
- View total active enrollment, institutional average attendance %, and counts of students in Safe, Warning, and Critical categories.
- Inspect the interactive **14-day attendance trajectory** line chart and **departmental comparison** bar chart.
- Review the high-priority follow-up list of critical students requiring immediate academic counseling.

### B. Student & Faculty Registries (`/admin-portal/students/`, `/admin-portal/faculty/`)
- Filter students by department, class section, or risk category.
- Search students instantly by roll number or name.
- View real-time cached attendance percentages and emergency contact numbers.

### C. Policy Thresholds Configuration (`/admin-portal/policies/`)
- Adjust institutional benchmarks:
  - **Minimum Attendance Required (%):** Default `75.0%`.
  - **Warning Threshold (%):** Default `80.0%`.
  - **Consecutive Absences Alert Limit:** Default `3` sessions.
  - **Correction Dispute Window:** Default `7` days.
- Saving policy changes automatically triggers synchronous recalculation of risk standings across all enrolled students.

### D. Excel Batch Import & Reports Export (`/admin-portal/import-export/`)
- **Download Template:** Generates `attendance_import_template.xlsx`.
- **Upload & Validate:** Parses uploaded spreadsheets, checks roll numbers and subject codes, and generates a validation preview with row-level error diagnostic banners.
- **Commit:** Atomically records valid rows into attendance tables and recalculates student statistics.
- **Export At-Risk Students:** Downloads sanitized `.xlsx` files with parent emergency contact information.

---

## 3. Faculty Portal Guide

### A. Mark Period Attendance (`/faculty-portal/mark-attendance/`)
1. Select class section, course, date, and period slot (P1 to P8).
2. Enter the lecture topic covered.
3. Toggle student statuses: **Present**, **Absent**, or **On-Duty**.
4. Use quick shortcuts: `Mark All Present` or `Mark All Absent`.
5. Click **Submit & Dispatch Alerts**:
   - Stores session records.
   - Recalculates student metrics.
   - Immediately dispatches notifications to linked parents for unexcused absences.

### B. Session History & Audited Corrections (`/faculty-portal/history/`)
- Review past lecture sessions.
- Modify individual records if necessary by providing a **mandatory audit reason**. Every status change is timestamped and recorded in the system audit trail.

### C. Leave & On-Duty Reviews (`/faculty-portal/leaves/`)
- Review student leave applications and On-Duty requests.
- Inspect attached proof documents (hackathon invitations, medical receipts).
- Click **Approve** or **Reject** with optional remarks to notify the student.

### D. Correction Dispute Reviews (`/faculty-portal/corrections/`)
- Inspect attendance dispute requests submitted by students.
- Approving a dispute automatically updates the attendance record and re-syncs student metrics.

---

## 4. Student Portal Guide

### A. Attendance Dashboard & Insights (`/student-portal/`)
- Overall attendance standing and visual risk badge.
- **Mathematical Recovery Insight:** Tells you exactly how many consecutive future classes you must attend to achieve 75%, or how many classes you can afford to miss while remaining safe.
- Subject-wise cards displaying attended vs. total periods.

### B. What-If Recovery Simulator (`/student-portal/simulator/`)
- Select any enrolled course or overall attendance.
- Enter hypothetical upcoming attended classes and hypothetical absences.
- Adjust your target goal (e.g. 75% or 80%).
- Click **Calculate Projected Standing** to see projected percentage, new risk level, and required sessions without altering real records.

### C. Apply for Leave or On-Duty (`/student-portal/leaves/`)
- Submit medical leaves or On-Duty permissions for competitions.
- Upload supporting documents (PDF, JPG, PNG).

### D. Dispute Attendance Records (`/student-portal/corrections/`)
- Select any recorded absence session and submit a dispute claim with your explanation for faculty review.

---

## 5. Parent Portal Guide

### A. Ward Monitoring (`/parent-portal/`)
- Real-time attendance percentage for all linked children.
- Clear visual badges (Safe, Warning, Critical).
- Log of recent unexcused absences.

### B. Absence History & Explanations (`/parent-portal/absences/`, `/parent-portal/submit-explanation/`)
- Review period-by-period absence dates.
- Submit parental explanation letters directly to faculty.

### C. Alert Preferences (`/parent-portal/preferences/`)
- Choose notification frequency: All Absences, Risk Warnings Only, or Daily Digest.
- Toggle SMS and Email alert channels.
