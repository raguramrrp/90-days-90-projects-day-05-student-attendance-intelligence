"""
Student Portal Views: Personal Attendance Analytics, Subject Breakdowns,
Recovery Simulator, Leave & OD Submissions, and Attendance Dispute Requests.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from .auth_views import student_required
from ..models import (
    StudentProfile, Subject, AttendanceRecord, AttendanceSession,
    LeaveRequest, AttendanceCorrectionRequest, LeaveType, AttendanceStatus,
    RiskLevel
)
from ..services.calculation_engine import (
    get_student_overall_attendance, get_student_subject_attendance,
    simulate_future_attendance, get_applicable_policy
)
from ..services.risk_engine import analyze_student_overall_risk


def _get_student_profile(user) -> StudentProfile:
    """Helper to retrieve student profile or first available if superuser."""
    if hasattr(user, 'student_profile'):
        return user.student_profile
    return StudentProfile.objects.first()


@student_required
def student_dashboard_view(request):
    """Personalized Student Attendance Intelligence Dashboard."""
    student = _get_student_profile(request.user)
    if not student:
        messages.error(request, "Student profile record not found.")
        return redirect('user_profile')

    overall_data = get_student_overall_attendance(student)
    
    # Enrolled subjects
    enrollments = student.enrollments.filter(is_active=True).select_related('subject')
    subject_cards = []
    for enr in enrollments:
        subj_attendance = get_student_subject_attendance(student, enr.subject)
        subject_cards.append(subj_attendance)

    # Recent attendance sessions
    recent_records = AttendanceRecord.objects.filter(
        student=student,
        session__is_cancelled=False
    ).select_related('session__subject', 'session__faculty__user').order_by('-session__date', '-session__period_number')[:8]

    context = {
        'student': student,
        'overall': overall_data,
        'subject_cards': subject_cards,
        'recent_records': recent_records,
        'active_nav': 'student_dashboard'
    }
    return render(request, 'student/dashboard.html', context)


@student_required
def student_my_attendance_view(request):
    """Detailed Subject-Wise Attendance Overview."""
    student = _get_student_profile(request.user)
    enrollments = student.enrollments.filter(is_active=True).select_related('subject')

    subject_rows = []
    for enr in enrollments:
        data = get_student_subject_attendance(student, enr.subject)
        subject_rows.append(data)

    context = {
        'student': student,
        'subject_rows': subject_rows,
        'active_nav': 'student_my_attendance'
    }
    return render(request, 'student/my_attendance.html', context)


@student_required
def student_subject_detail_view(request, subject_id):
    """Detailed Period-by-Period Attendance History for a Selected Subject."""
    student = _get_student_profile(request.user)
    subject = get_object_or_404(Subject, id=subject_id)

    records = AttendanceRecord.objects.filter(
        student=student,
        session__subject=subject,
        session__is_cancelled=False
    ).select_related('session').order_by('-session__date', '-session__period_number')

    subject_data = get_student_subject_attendance(student, subject)

    context = {
        'student': student,
        'subject': subject,
        'subject_data': subject_data,
        'records': records,
        'active_nav': 'student_my_attendance'
    }
    return render(request, 'student/subject_detail.html', context)


@student_required
def student_attendance_simulator_view(request):
    """
    Interactive Attendance Recovery Simulator.
    Allows students to run hypothetical 'what-if' scenarios without altering real database records.
    """
    student = _get_student_profile(request.user)
    enrollments = student.enrollments.filter(is_active=True).select_related('subject')

    # Selected subject or overall
    subject_id = request.GET.get('subject_id')
    selected_subject = None
    if subject_id and subject_id != 'overall':
        selected_subject = Subject.objects.filter(id=subject_id).first()

    if selected_subject:
        current_data = get_student_subject_attendance(student, selected_subject)
        curr_attended = current_data['stats']['effective_attended']
        curr_total = current_data['stats']['total_eligible']
        target_pct = current_data['target_percentage']
    else:
        current_data = get_student_overall_attendance(student)
        curr_attended = current_data['stats']['effective_attended']
        curr_total = current_data['stats']['total_eligible']
        target_pct = current_data['target_percentage']

    # Simulation Inputs
    sim_result = None
    if request.method == 'POST':
        try:
            future_attended = int(request.POST.get('future_attended', 0))
            future_absent = int(request.POST.get('future_absent', 0))
            custom_target = float(request.POST.get('target_percentage', target_pct))
            
            sim_result = simulate_future_attendance(
                effective_attended=curr_attended,
                total_eligible=curr_total,
                future_attended=future_attended,
                future_absent=future_absent,
                target_percentage=custom_target
            )
        except (ValueError, TypeError):
            messages.error(request, "Please enter valid numbers for simulation parameters.")

    context = {
        'student': student,
        'enrollments': enrollments,
        'selected_subject': selected_subject,
        'current_data': current_data,
        'curr_attended': curr_attended,
        'curr_total': curr_total,
        'target_pct': target_pct,
        'sim_result': sim_result,
        'active_nav': 'student_attendance_simulator'
    }
    return render(request, 'student/simulator.html', context)


@student_required
def student_leave_requests_view(request):
    """Submit and Track Leave & On-Duty (OD) Requests."""
    student = _get_student_profile(request.user)

    if request.method == 'POST':
        req_type = request.POST.get('request_type', LeaveType.LEAVE)
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        reason = request.POST.get('reason', '').strip()
        doc = request.FILES.get('supporting_document')

        if not (start_date_str and end_date_str and reason):
            messages.error(request, "Please complete all mandatory fields.")
        elif start_date_str > end_date_str:
            messages.error(request, "End date cannot be prior to start date.")
        else:
            LeaveRequest.objects.create(
                student=student,
                request_type=req_type,
                start_date=start_date_str,
                end_date=end_date_str,
                reason=reason,
                supporting_document=doc
            )
            messages.success(request, "Your leave/OD request has been submitted for faculty review.")
            return redirect('student_leave_requests')

    leaves = LeaveRequest.objects.filter(student=student).order_by('-created_at')

    context = {
        'student': student,
        'leaves': leaves,
        'leave_types': LeaveType.choices,
        'active_nav': 'student_leave_requests'
    }
    return render(request, 'student/leave_requests.html', context)


@student_required
def student_correction_requests_view(request):
    """Submit and Track Attendance Correction Disputes."""
    student = _get_student_profile(request.user)

    if request.method == 'POST':
        record_id = request.POST.get('record_id')
        requested_status = request.POST.get('requested_status', AttendanceStatus.PRESENT)
        reason = request.POST.get('reason', '').strip()

        rec = get_object_or_404(AttendanceRecord, id=record_id, student=student)

        # Check if already has a pending correction
        if AttendanceCorrectionRequest.objects.filter(attendance_record=rec, status='PENDING').exists():
            messages.warning(request, "A pending correction dispute already exists for this attendance session.")
        elif not reason:
            messages.error(request, "Please provide an explanation reason for the correction dispute.")
        else:
            AttendanceCorrectionRequest.objects.create(
                attendance_record=rec,
                student=student,
                requested_status=requested_status,
                reason=reason
            )
            messages.success(request, "Attendance correction dispute submitted successfully.")
            return redirect('student_correction_requests')

    corrections = AttendanceCorrectionRequest.objects.filter(student=student).select_related(
        'attendance_record__session__subject'
    ).order_by('-created_at')

    # Find candidate absence records eligible for dispute
    candidate_records = AttendanceRecord.objects.filter(
        student=student,
        status=AttendanceStatus.ABSENT
    ).select_related('session__subject').order_by('-session__date', '-session__period_number')[:20]

    context = {
        'student': student,
        'corrections': corrections,
        'candidate_records': candidate_records,
        'active_nav': 'student_correction_requests'
    }
    return render(request, 'student/correction_requests.html', context)
