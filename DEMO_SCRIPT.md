# 90-Second Demonstration Script & Video Guide

This script is structured for live placement interviews, hackathon demos, and recruiter portfolio presentations.

---

## Preparation (10 Seconds)
1. Run `run.bat` (or execute `.\.venv\Scripts\python manage.py runserver`).
2. Navigate to `http://127.0.0.1:8000/`.

---

## Step 1: Institutional Command Center (30 Seconds)
1. On the login screen, click the **"👑 Administrator"** quick-fill button, then click **Sign In**.
2. **Point out:**
   - The visual identity: Warm Ivory (`#F7F5EF`), Forest Green (`#24483D`), Sage, and Terracotta styling.
   - The **Executive Metric Cards**: Total enrollment, period-weighted institutional average attendance, and live counts of Safe, Warning, and Critical students.
   - The **14-Day Attendance Trajectory** chart showing real aggregate attendance trends against the 75% benchmark.
   - The **Eligibility Distribution** donut chart.
3. Click **"Excel Import / Export"** in the sidebar. Show how uploaded spreadsheets are parsed, validated row-by-row, and checked for invalid students or formula injection risks before committing.

---

## Step 2: Faculty Period-Wise Attendance & Dispute Review (30 Seconds)
1. Click the top-right user menu &rarr; **Log Out**.
2. Click the **"🎓 Faculty (Prof. Ananya)"** button and sign in.
3. In the sidebar, click **"Mark Attendance"**:
   - Show how faculty select the Class Section, Subject, Date, and Period (P1 to P8).
   - Use the **"Mark All Present"** shortcut, toggle student `23AI014` to **Absent**, and enter topic: *"Backpropagation & Gradient Descent"*.
   - Click **"Submit & Dispatch Alerts"**: point out how student standing recalculates instantly and parent alert records are generated.
4. Click **"Correction Disputes"** in the sidebar to show the audit queue where faculty review absence appeals submitted by students.

---

## Step 3: Student Attendance Simulator & Recovery Projections (30 Seconds)
1. Sign out and click **"⚠️ Student (Critical 68%)"** to log in as **Rohan Verma (`23AI014`)**.
2. **Point out:**
   - The prominent **Critical Debarment Risk** indicator.
   - The **Mathematical Recovery Insight**: *"To recover above the mandatory 75.0% threshold, student must attend the next 15 consecutive scheduled sessions without absence."*
3. Click **"Recovery Simulator"** in the top header:
   - Enter `15` in "Classes to Attend" and `0` in "Absences".
   - Click **"Calculate Projected Standing"**.
   - Show how the projected attendance climbs to `75.0%` (Safe Standing), showing students an actionable, transparent roadmap to recovery.
4. Show the **"Apply Leave / OD"** screen where students upload proof for hackathons and medical leaves.

---

## Step 4: Parent Portal & Absence Visibility (15 Seconds)
1. Sign out and click **"👨‍👧 Parent (Mr. Rajesh Sharma)"** and sign in.
2. Show the parent's view of linked ward **Aarav Sharma (`23AI001`)** with a 92% safe standing.
3. Show the **Notification Center** bell with real-time absence alerts and the **"Submit Absence Explanation"** form.

---

## Key Talking Points for Recruiters & Interviewers
- *"This isn't a mock calculator; it's a normalized 22-table relational system with role-based access control and transactional data integrity."*
- *"We treat period attendance with precision: missing one period does not penalize the whole day."*
- *"The recovery formula is mathematically proven: $\lceil (T \cdot N - P) / (1 - T) \rceil$."*
- *"Every feature has been tested with 25 automated unit and integration tests passing with 100% reliability."*
