"""
Accurate Attendance Calculation Engine.
Implements exact mathematical formulas for attendance percentage,
recovery session requirements, margin-of-absence thresholds, and what-if simulation.
"""

import math
from typing import Dict, Any, Optional
from django.db.models import Count, Q
from ..models import (
    StudentProfile, Subject, AttendanceRecord, AttendanceStatus,
    AttendancePolicy, ClassSection
)


def get_applicable_policy(department=None) -> AttendancePolicy:
    """Returns department policy or institutional global default policy."""
    if department:
        policy = AttendancePolicy.objects.filter(department=department).first()
        if policy:
            return policy
    global_policy = AttendancePolicy.objects.filter(department__isnull=True).first()
    if global_policy:
        return global_policy
    # Fallback default if not seeded
    return AttendancePolicy(min_attendance_percentage=75.0, warning_threshold=80.0)


def calculate_session_stats(present: int, excused: int, total_eligible: int) -> Dict[str, Any]:
    """
    Computes attendance percentage given present, excused, and total sessions.
    Excused (On-Duty/Medical) counts towards attended sessions per standard institutional policy.
    """
    if total_eligible <= 0:
        return {
            'present_count': 0,
            'excused_count': 0,
            'absent_count': 0,
            'total_eligible': 0,
            'effective_attended': 0,
            'percentage': 100.0,
            'has_sessions': False,
        }

    effective_attended = present + excused
    absent_count = max(0, total_eligible - effective_attended)
    percentage = round((effective_attended / total_eligible) * 100.0, 2)
    percentage = min(100.0, max(0.0, percentage))

    return {
        'present_count': present,
        'excused_count': excused,
        'absent_count': absent_count,
        'total_eligible': total_eligible,
        'effective_attended': effective_attended,
        'percentage': percentage,
        'has_sessions': True,
    }


def calculate_recovery_projections(
    effective_attended: int,
    total_eligible: int,
    target_percentage: float = 75.0,
    remaining_scheduled_sessions: Optional[int] = None
) -> Dict[str, Any]:
    """
    Computes:
    1. Minimum consecutive sessions needed to reach target percentage T.
       Formula: max(0, ceil((T * N - P) / (1 - T))) where T is decimal.
    2. Maximum additional sessions that can be missed while remaining >= target.
       Formula: max(0, floor((P - T * N) / T)) where T is decimal.
    3. Recovery feasibility given remaining scheduled sessions.
    """
    t_dec = target_percentage / 100.0
    p = effective_attended
    n = total_eligible

    # Edge Case: No sessions held yet
    if n <= 0:
        return {
            'target_percentage': target_percentage,
            'current_percentage': 100.0,
            'is_target_met': True,
            'sessions_needed': 0,
            'max_absences_permitted': 0,
            'is_recovery_possible': True,
            'explanation': "No class sessions have been recorded yet. Student is currently in good standing.",
        }

    current_pct = round((p / n) * 100.0, 2)
    is_target_met = current_pct >= target_percentage

    # 1. Sessions needed to reach target
    if is_target_met:
        sessions_needed = 0
    elif t_dec >= 1.0:
        # Target is 100%, but student has already missed at least one class
        sessions_needed = -1
    else:
        num = (t_dec * n) - p
        den = 1.0 - t_dec
        sessions_needed = max(0, math.ceil(num / den))

    # 2. Maximum additional absences permitted while remaining >= target
    if not is_target_met:
        max_absences_permitted = 0
    elif t_dec <= 0.0:
        max_absences_permitted = 999
    else:
        max_absences_permitted = max(0, math.floor((p - (t_dec * n)) / t_dec))

    # 3. Feasibility check with remaining sessions
    is_recovery_possible = True
    recovery_note = ""

    if sessions_needed == -1:
        is_recovery_possible = False
        recovery_note = "A target of 100% cannot be achieved because previous absences have already been recorded."
    elif remaining_scheduled_sessions is not None:
        if sessions_needed > remaining_scheduled_sessions:
            is_recovery_possible = False
            recovery_note = (
                f"Eligibility impossible within remaining term: student requires {sessions_needed} consecutive attended sessions, "
                f"but only {remaining_scheduled_sessions} sessions remain on the academic timetable."
            )
        else:
            is_recovery_possible = True
            recovery_note = (
                f"Recovery feasible: student must attend at least {sessions_needed} of the next {remaining_scheduled_sessions} sessions."
            )
    else:
        if sessions_needed > 0:
            recovery_note = f"Student must attend the next {sessions_needed} consecutive sessions without absence to reach {target_percentage}%."
        else:
            recovery_note = f"Attendance is above the {target_percentage}% threshold. Student can miss at most {max_absences_permitted} additional sessions."

    return {
        'target_percentage': target_percentage,
        'current_percentage': current_pct,
        'is_target_met': is_target_met,
        'sessions_needed': sessions_needed,
        'max_absences_permitted': max_absences_permitted,
        'is_recovery_possible': is_recovery_possible,
        'explanation': recovery_note,
    }


def simulate_future_attendance(
    effective_attended: int,
    total_eligible: int,
    future_attended: int,
    future_absent: int,
    target_percentage: float = 75.0
) -> Dict[str, Any]:
    """
    Pure mathematical simulator: does NOT modify any database records.
    Simulates:
    new_attended = effective_attended + future_attended
    new_total = total_eligible + future_attended + future_absent
    """
    sim_attended = effective_attended + max(0, future_attended)
    sim_total = total_eligible + max(0, future_attended) + max(0, future_absent)

    stats = calculate_session_stats(
        present=sim_attended,
        excused=0,
        total_eligible=sim_total
    )

    projections = calculate_recovery_projections(
        effective_attended=sim_attended,
        total_eligible=sim_total,
        target_percentage=target_percentage
    )

    from .risk_engine import classify_risk_level

    projected_risk = classify_risk_level(stats['percentage'], target_percentage=target_percentage)

    return {
        'initial_attended': effective_attended,
        'initial_total': total_eligible,
        'future_attended_input': future_attended,
        'future_absent_input': future_absent,
        'projected_attended': sim_attended,
        'projected_total': sim_total,
        'projected_percentage': stats['percentage'],
        'projected_risk': projected_risk,
        'target_percentage': target_percentage,
        'sessions_needed_after': projections['sessions_needed'],
        'max_further_absences': projections['max_absences_permitted'],
        'is_recovery_possible': projections['is_recovery_possible'],
        'explanation': projections['explanation'],
    }


def get_student_subject_attendance(student: StudentProfile, subject: Subject) -> Dict[str, Any]:
    """Calculates attendance for a specific student in a specific subject."""
    records = AttendanceRecord.objects.filter(
        student=student,
        session__subject=subject,
        session__is_cancelled=False
    ).select_related('session')

    total = records.count()
    present = records.filter(status=AttendanceStatus.PRESENT).count()
    excused = records.filter(status=AttendanceStatus.EXCUSED).count()
    absent = records.filter(status=AttendanceStatus.ABSENT).count()

    stats = calculate_session_stats(present, excused, total)

    policy = get_applicable_policy(subject.department)
    target = subject.min_attendance_threshold or policy.min_attendance_percentage

    projections = calculate_recovery_projections(
        effective_attended=stats['effective_attended'],
        total_eligible=stats['total_eligible'],
        target_percentage=target
    )

    from .risk_engine import classify_risk_level, analyze_subject_risk

    risk_info = analyze_subject_risk(student, subject, stats['percentage'], target)

    return {
        'subject': subject,
        'stats': stats,
        'projections': projections,
        'risk_info': risk_info,
        'target_percentage': target,
    }


def get_student_overall_attendance(student: StudentProfile) -> Dict[str, Any]:
    """Calculates overall aggregated attendance across all enrolled subjects."""
    records = AttendanceRecord.objects.filter(
        student=student,
        session__is_cancelled=False
    ).select_related('session', 'session__subject')

    total = records.count()
    present = records.filter(status=AttendanceStatus.PRESENT).count()
    excused = records.filter(status=AttendanceStatus.EXCUSED).count()
    absent = records.filter(status=AttendanceStatus.ABSENT).count()

    stats = calculate_session_stats(present, excused, total)

    dept = student.class_section.department if student.class_section else None
    policy = get_applicable_policy(dept)
    target = policy.min_attendance_percentage

    projections = calculate_recovery_projections(
        effective_attended=stats['effective_attended'],
        total_eligible=stats['total_eligible'],
        target_percentage=target
    )

    from .risk_engine import classify_risk_level, analyze_student_overall_risk

    risk_info = analyze_student_overall_risk(student, stats['percentage'], policy)

    return {
        'student': student,
        'stats': stats,
        'projections': projections,
        'risk_info': risk_info,
        'policy': policy,
        'target_percentage': target,
    }


def recalculate_and_sync_student_metrics(student: StudentProfile) -> StudentProfile:
    """Updates and persists cached attendance percentage and risk level on StudentProfile."""
    overall = get_student_overall_attendance(student)
    student.cached_attendance_percentage = overall['stats']['percentage']
    student.cached_risk_level = overall['risk_info']['risk_level']
    student.save(update_fields=['cached_attendance_percentage', 'cached_risk_level', 'last_calculated_at'])
    return student
