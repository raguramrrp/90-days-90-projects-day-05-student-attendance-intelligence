# Project Overview: Student Attendance Intelligence & Early Warning System

## 1. Executive Summary

The **Student Attendance Intelligence & Early Warning System** is an enterprise-grade educational technology web platform designed for higher education institutions. Rather than treating attendance as a static bookkeeping tally or generic percentage calculator, this platform transforms period-by-period class attendance into an actionable, proactive early-warning engine.

Built for my **90 Days – 90 Projects Challenge (Day 5)**, this system addresses student absenteeism, debarment risks, parental disconnect, and administrative workflow friction through four dedicated role-based portals: **Administrator**, **Faculty**, **Student**, and **Parent**.

---

## 2. Problem Statement

Across collegiate institutions:
1. **Late Interventions:** Students and parents discover attendance shortages only days before final examinations when debarment is already unavoidable.
2. **Coarse-Grained Tracking:** Daily attendance systems fail to recognize that a student who misses one period for a laboratory or appointment was physically present for the rest of the day.
3. **Dispute Inefficiencies:** Correction of roll-call errors or sanctioned On-Duty (OD) participation (hackathons, symposiums, sports) often requires physical signatures across multiple department offices, creating lost paper trails and administrative overhead.
4. **Parental Disconnect:** Parents lack visibility into their wards' daily classroom attendance, receiving low-attendance notices only when eligibility is already critical.

---

## 3. Solution Pillars

- **Period-Wise Attendance Engine:** Discrete tracking of individual timetable slots (P1 to P8). A single missed hour does not penalize an entire day.
- **Mathematical Recovery Projections:** Transparent mathematical calculations indicating the exact number of consecutive upcoming sessions required to recover eligibility, or the maximum permissible absences remaining.
- **Explainable Multi-Signal Risk Classification:** Categorizes students into **Safe**, **Warning**, and **Critical** using rule-based reasoning, absence velocities, and consecutive absence triggers.
- **Automated Immediate Parent Notifications:** Multi-channel alerting (in-app, email, and simulated SMS/WhatsApp sandbox) dispatched immediately upon an unexcused absence.
- **Full Digital Lifecycle:** Closed-loop request-review workflows for Leave/OD applications and attendance correction disputes with full audit trails.
- **Institutional Analytics:** Live dashboard featuring aggregated metrics, 14-day absence trajectories, and departmental comparisons.

---

## 4. Target User Personas

| Role | Primary Objectives | Key Capabilities |
| :--- | :--- | :--- |
| **Administrator** | Institutional compliance, policy governance, batch data handling | Dashboard analytics, policy adjustments, timetable scheduling, Excel import/export, audit logs |
| **Faculty** | Fast classroom marking, at-risk interventions, request review | Period marking with bulk toggles, session history edits with audit reasons, leave/dispute approvals |
| **Student** | Transparency, eligibility tracking, what-if planning | Subject breakdowns, attendance recovery simulator, leave/OD submissions, dispute filings |
| **Parent** | Real-time ward monitoring, absence accountability | Multi-ward dashboard, absence logs, formal absence explanation submissions, alert preferences |

---

## 5. Scope & MVP Boundaries

### Core MVP Deliverables (Complete & Fully Functional):
- Full 4-portal role-based access control with server-side authorization.
- 22 normalized relational database entities.
- Exact recovery formulas ($\lceil (T \times N - P) / (1 - T) \rceil$) and margin-of-absence calculations ($\lfloor (P - T \times N) / T \rfloor$).
- What-If Attendance Recovery Simulator.
- Excel batch import validation engine with row-level error reporting and formula injection protection.
- Database-backed notification engine with simulation delivery logs.
- Decision Tree ML extension with confusion matrix evaluations.
- 25 automated unit and integration tests.

### Future Roadmap:
- Production Twilio / WhatsApp Business Cloud API integration.
- Biometric & RFID hardware terminal integration.
- Multi-campus tenant isolation.
