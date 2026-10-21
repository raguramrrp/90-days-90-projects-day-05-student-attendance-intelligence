"""
Explainable Attendance Risk Classification Engine.
Implements transparent rule-based risk classification, attendance trend analysis,
and multi-signal early warning diagnostics.
"""

from typing import Dict, Any, List
from datetime import timedelta
from django.utils import timezone
from ..models import (
    RiskLevel, StudentProfile, Subject, AttendanceRecord, AttendanceStatus,
    AttendancePolicy
)


def classify_risk_level(
    percentage: float,
    target_percentage: float = 75.0,
    warning_threshold: float = 80.0
) -> str:
    """Classifies risk level based on threshold parameters."""
    if percentage < target_percentage:
        return RiskLevel.CRITICAL
    elif percentage < warning_threshold:
        return RiskLevel.WARNING
    else:
        return RiskLevel.SAFE


def analyze_recent_absence_trend(student: StudentProfile, subject: Subject = None, limit: int = 10) -> Dict[str, Any]:
    """
    Evaluates recent attendance records to detect:
    - consecutive recent absences
    - recent attendance trajectory (improving, stable, deteriorating)
    - absence velocity (missed periods in last 14 days)
    """
    query = AttendanceRecord.objects.filter(
        student=student,
        session__is_cancelled=False
    ).select_related('session').order_by('-session__date', '-session__period_number')

    if subject:
        query = query.filter(session__subject=subject)

    recent_records = list(query[:limit])

    # 1. Consecutive absences right now
    consecutive_absences = 0
    for rec in recent_records:
        if rec.status == AttendanceStatus.ABSENT:
            consecutive_absences += 1
        else:
            break

    # 2. Absences in the last 14 days
    two_weeks_ago = timezone.now().date() - timedelta(days=14)
    last_14_days_records = [r for r in recent_records if r.session.date >= two_weeks_ago]
    last_14_absences = sum(1 for r in last_14_days_records if r.status == AttendanceStatus.ABSENT)
    last_14_total = len(last_14_days_records)
    last_14_rate = round((last_14_absences / last_14_total) * 100, 1) if last_14_total > 0 else 0.0

    # 3. Trajectory analysis: compare last 5 vs previous 5
    first_half = recent_records[:5]
    second_half = recent_records[5:10]

    rate_first = sum(1 for r in first_half if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.EXCUSED)) / len(first_half) if first_half else 1.0
    rate_second = sum(1 for r in second_half if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.EXCUSED)) / len(second_half) if second_half else 1.0

    if rate_first < rate_second - 0.15:
        trajectory = "DETERIORATING"
        trajectory_label = "Declining Trend (Recent High Absence Rate)"
    elif rate_first > rate_second + 0.15:
        trajectory = "IMPROVING"
        trajectory_label = "Improving Trend (Consistent Recent Attendance)"
    else:
        trajectory = "STABLE"
        trajectory_label = "Stable Trajectory"

    return {
        'consecutive_absences': consecutive_absences,
        'recent_14_days_absences': last_14_absences,
        'recent_14_days_total': last_14_total,
        'recent_14_days_absence_rate': last_14_rate,
        'trajectory': trajectory,
        'trajectory_label': trajectory_label,
    }


def analyze_student_overall_risk(
    student: StudentProfile,
    current_percentage: float,
    policy: AttendancePolicy
) -> Dict[str, Any]:
    """
    Evaluates comprehensive multi-signal risk for a student.
    Returns structured explanation, signal weights, and recommendation.
    """
    min_threshold = policy.min_attendance_percentage
    warn_threshold = policy.warning_threshold
    consecutive_alert_limit = policy.consecutive_absence_alert_count

    trend = analyze_recent_absence_trend(student, limit=10)
    consecutive_absences = trend['consecutive_absences']

    reasons: List[str] = []
    signals: List[Dict[str, str]] = []

    # Baseline classification
    base_risk = classify_risk_level(current_percentage, min_threshold, warn_threshold)

    # Signal 1: Percentage vs Target
    delta = round(current_percentage - min_threshold, 1)
    if current_percentage < min_threshold:
        reasons.append(f"Overall attendance ({current_percentage}%) is strictly below the mandatory institutional minimum of {min_threshold}%.")
        signals.append({'type': 'CRITICAL', 'label': f"Deficit: {abs(delta)}% below eligibility cut-off"})
    elif current_percentage < warn_threshold:
        reasons.append(f"Overall attendance ({current_percentage}%) is in the caution window ({min_threshold}% - {warn_threshold}%).")
        signals.append({'type': 'WARNING', 'label': f"Thin Buffer: Only {delta}% above debarment limit"})
    else:
        reasons.append(f"Overall attendance ({current_percentage}%) is comfortably above the warning boundary ({warn_threshold}%).")
        signals.append({'type': 'SAFE', 'label': f"Safe Buffer: {delta}% surplus above threshold"})

    # Signal 2: Consecutive Absences Early Warning
    if consecutive_absences >= consecutive_alert_limit:
        reasons.append(f"Student has accumulated {consecutive_absences} consecutive unexcused session absences.")
        signals.append({'type': 'WARNING', 'label': f"{consecutive_absences} consecutive missed sessions"})
        # Elevate Safe to Warning if consecutive absence run is high
        if base_risk == RiskLevel.SAFE:
            base_risk = RiskLevel.WARNING

    # Signal 3: Recent Velocity / Trajectory
    if trend['trajectory'] == 'DETERIORATING':
        reasons.append("Recent 2-week attendance shows a steep downward trend.")
        signals.append({'type': 'WARNING', 'label': "Negative momentum in last 10 periods"})
    elif trend['trajectory'] == 'IMPROVING':
        signals.append({'type': 'SAFE', 'label': "Positive recovery momentum"})

    # Final Risk Level
    final_risk = base_risk

    # Recommendation
    if final_risk == RiskLevel.CRITICAL:
        recommendation = "Immediate faculty intervention and official parent notification required. Urgent attendance recovery plan must be activated."
    elif final_risk == RiskLevel.WARNING:
        recommendation = "Student should be cautioned against further unexcused absences. Monitor upcoming timetable sessions closely."
    else:
        recommendation = "Student maintains satisfactory attendance. Continue consistent engagement."

    return {
        'risk_level': final_risk,
        'risk_label': dict(RiskLevel.choices).get(final_risk, final_risk),
        'current_percentage': current_percentage,
        'min_threshold': min_threshold,
        'warning_threshold': warn_threshold,
        'reasons': reasons,
        'signals': signals,
        'trend': trend,
        'recommendation': recommendation,
    }


def analyze_subject_risk(
    student: StudentProfile,
    subject: Subject,
    current_percentage: float,
    min_threshold: float = 75.0,
    warn_threshold: float = 80.0
) -> Dict[str, Any]:
    """Subject-specific explainable risk assessment."""
    trend = analyze_recent_absence_trend(student, subject=subject, limit=8)
    base_risk = classify_risk_level(current_percentage, min_threshold, warn_threshold)

    reasons: List[str] = []
    if current_percentage < min_threshold:
        reasons.append(f"Attendance in {subject.code} ({current_percentage}%) is below course prerequisite ({min_threshold}%).")
    elif current_percentage < warn_threshold:
        reasons.append(f"Attendance in {subject.code} ({current_percentage}%) is in pre-debarment buffer zone.")
    else:
        reasons.append(f"Satisfactory standing in {subject.code} ({current_percentage}% >= {warn_threshold}%).")

    if trend['consecutive_absences'] >= 2:
        reasons.append(f"Missed {trend['consecutive_absences']} consecutive sessions in this subject.")
        if base_risk == RiskLevel.SAFE:
            base_risk = RiskLevel.WARNING

    return {
        'subject_code': subject.code,
        'risk_level': base_risk,
        'current_percentage': current_percentage,
        'min_threshold': min_threshold,
        'reasons': reasons,
        'trend': trend,
    }
