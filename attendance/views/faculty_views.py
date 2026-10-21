"""
Faculty Portal Views: Period-Wise Attendance Marking, Session History & Audited Edits,
At-Risk Interventions, and Leave & Correction Request Approvals.
"""

from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse

from .auth_views import faculty_required
from ..models import (
    FacultyProfile, FacultySubjectAssignment, ClassSection, Subject,
    AttendanceSession, AttendanceRecord, AttendanceStatus, SessionStatus,
    StudentProfile, LeaveRequest, AttendanceCorrectionRequest, AuditLog,
    RiskLevel, TimetableSession
)
from ..services.calculation_engine import recalculate_and_sync_student_metrics
from ..services.notification_service import (
    notify_parents_of_absence, notify_leave_status_update, notify_correction_status_update
)
from ..services.excel_service import export_subject_attendance_excel


def _get_faculty_profile(user) -> FacultyProfile:
    """Helper to retrieve faculty profile or first available if superuser."""
    if hasattr(user, 'faculty_profile'):
        return user.faculty_profile
    return FacultyProfile.objects.first()


@faculty_required
def faculty_dashboard_view(request):
    """Faculty Overview: Assigned subjects, today's schedule, at-risk alerts, pending reviews."""
    faculty = _get_faculty_profile(request.user)
    assignments = FacultySubjectAssignment.objects.filter(
        faculty=faculty, is_active=True
    ).select_related('subject', 'class_section')

    assigned_classes = [a.class_section for a in assignments]
    assigned_subjects = [a.subject for a in assignments]

    # Today's Timetable
    today_weekday = timezone.now().weekday()
    today_sessions = TimetableSession.objects.filter(
        faculty=faculty,
        day_of_week=today_weekday
    ).select_related('class_section', 'subject').order_by('period_number')

    # Students at risk in faculty's assigned classes
    at_risk_students = StudentProfile.objects.filter(
        class_section__in=assigned_classes,
        cached_risk_level__in=[RiskLevel.WARNING, RiskLevel.CRITICAL]
    ).select_related('user', 'class_section')[:8]

    # Pending reviews
    pending_leaves = LeaveRequest.objects.filter(
        student__class_section__in=assigned_classes,
        status='PENDING'
    ).count()

    pending_corrections = AttendanceCorrectionRequest.objects.filter(
        attendance_record__session__subject__in=assigned_subjects,
        status='PENDING'
    ).count()

    # Recent marked sessions
    recent_sessions = AttendanceSession.objects.filter(
        faculty=faculty
    ).select_related('subject', 'class_section').order_by('-date', '-period_number')[:5]

    context = {
        'faculty': faculty,
        'assignments': assignments,
        'today_sessions': today_sessions,
        'at_risk_students': at_risk_students,
        'pending_leaves': pending_leaves,
        'pending_corrections': pending_corrections,
        'recent_sessions': recent_sessions,
        'active_nav': 'faculty_dashboard'
    }
    return render(request, 'faculty/dashboard.html', context)


@faculty_required
def faculty_mark_attendance_view(request):
    """
    Period-wise attendance recording interface.
    Validates period, loads enrolled students, supports bulk toggles,
    prevents silent overwrites, updates student metrics, and alerts parents on unexcused absences.
    """
    faculty = _get_faculty_profile(request.user)
    assignments = FacultySubjectAssignment.objects.filter(
        faculty=faculty, is_active=True
    ).select_related('subject', 'class_section')

    # Selected parameters
    class_id = request.GET.get('class_id') or (assignments.first().class_section_id if assignments.exists() else None)
    subject_id = request.GET.get('subject_id') or (assignments.first().subject_id if assignments.exists() else None)
    date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    period_num = int(request.GET.get('period', 1))

    selected_class = ClassSection.objects.filter(id=class_id).first() if class_id else None
    selected_subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

    try:
        session_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        session_date = timezone.now().date()

    existing_session = None
    existing_records_map = {}
    if selected_class and selected_subject:
        existing_session = AttendanceSession.objects.filter(
            class_section=selected_class,
            subject=selected_subject,
            date=session_date,
            period_number=period_num
        ).first()

        if existing_session:
            existing_records = existing_session.records.all()
            existing_records_map = {r.student_id: r.status for r in existing_records}

    # Load enrolled students
    students = []
    if selected_class:
        students = selected_class.students.all().select_related('user').order_by('roll_number')

    if request.method == 'POST':
        action_type = request.POST.get('action_type', 'submit')
        topic_covered = request.POST.get('topic_covered', '').strip()

        with transaction.atomic():
            session, created = AttendanceSession.objects.get_or_create(
                class_section=selected_class,
                subject=selected_subject,
                date=session_date,
                period_number=period_num,
                defaults={
                    'faculty': faculty,
                    'topic_covered': topic_covered,
                    'status': SessionStatus.SUBMITTED if action_type == 'submit' else SessionStatus.DRAFT,
                    'submitted_by': request.user
                }
            )

            if not created:
                session.topic_covered = topic_covered
                session.status = SessionStatus.SUBMITTED if action_type == 'submit' else SessionStatus.DRAFT
                session.submitted_by = request.user
                session.save()

            affected_students = []

            for st in students:
                status_key = f"student_{st.id}"
                status_val = request.POST.get(status_key, AttendanceStatus.PRESENT)
                remarks_val = request.POST.get(f"remarks_{st.id}", '').strip()

                rec, _ = AttendanceRecord.objects.update_or_create(
                    session=session,
                    student=st,
                    defaults={
                        'status': status_val,
                        'remarks': remarks_val,
                        'recorded_by': request.user
                    }
                )
                affected_students.append(st)

                # Send parent absence alerts immediately if unexcused absence
                if status_val == AttendanceStatus.ABSENT and action_type == 'submit':
                    notify_parents_of_absence(rec)

            # Audit Log
            AuditLog.objects.create(
                user=request.user,
                action="MARK_PERIOD_ATTENDANCE",
                model_name="AttendanceSession",
                object_id=str(session.id),
                details=f"Marked P{period_num} for {selected_subject.code} on {session_date} ({len(students)} students)."
            )

        # Recalculate metrics for all students in class
        for st in affected_students:
            recalculate_and_sync_student_metrics(st)

        messages.success(request, f"Attendance for Period {period_num} ({selected_subject.code}) recorded successfully.")
        return redirect(f"{request.path}?class_id={selected_class.id}&subject_id={selected_subject.id}&date={session_date}&period={period_num}")

    context = {
        'assignments': assignments,
        'selected_class': selected_class,
        'selected_subject': selected_subject,
        'session_date': session_date.strftime('%Y-%m-%d'),
        'period_num': period_num,
        'period_range': range(1, 9),
        'students': students,
        'existing_session': existing_session,
        'existing_records_map': existing_records_map,
        'status_choices': AttendanceStatus.choices,
        'active_nav': 'faculty_mark_attendance'
    }
    return render(request, 'faculty/mark_attendance.html', context)


@faculty_required
def faculty_attendance_history_view(request):
    """View and authorized editing of previously recorded attendance sessions with mandatory audit reason."""
    faculty = _get_faculty_profile(request.user)

    if request.method == 'POST' and 'edit_record' in request.POST:
        record_id = request.POST.get('record_id')
        new_status = request.POST.get('new_status')
        change_reason = request.POST.get('change_reason', '').strip()

        if not change_reason:
            messages.error(request, "A mandatory reason is required to modify an existing attendance record.")
        else:
            rec = get_object_or_404(AttendanceRecord, id=record_id)
            old_status = rec.status
            rec.status = new_status
            rec.remarks = f"Edited by {faculty.user.get_full_name() or faculty.user.username}: {change_reason}"
            rec.save(update_fields=['status', 'remarks', 'updated_at'])

            AuditLog.objects.create(
                user=request.user,
                action="MANUAL_ATTENDANCE_CORRECTION",
                model_name="AttendanceRecord",
                object_id=str(rec.id),
                details=f"Status changed from {old_status} to {new_status}. Reason: {change_reason}"
            )

            # Recalculate student metrics
            recalculate_and_sync_student_metrics(rec.student)
            messages.success(request, f"Attendance status for {rec.student.roll_number} updated to {rec.get_status_display()}.")

        return redirect('faculty_attendance_history')

    sessions = AttendanceSession.objects.filter(
        faculty=faculty
    ).select_related('subject', 'class_section').order_by('-date', '-period_number')

    selected_session_id = request.GET.get('session_id')
    selected_session = None
    session_records = []
    if selected_session_id:
        selected_session = get_object_or_404(AttendanceSession, id=selected_session_id, faculty=faculty)
        session_records = selected_session.records.all().select_related('student__user').order_by('student__roll_number')

    context = {
        'sessions': sessions,
        'selected_session': selected_session,
        'session_records': session_records,
        'status_choices': AttendanceStatus.choices,
        'active_nav': 'faculty_attendance_history'
    }
    return render(request, 'faculty/attendance_history.html', context)


@faculty_required
def faculty_at_risk_view(request):
    """Students at risk in faculty's assigned courses with recovery recommendations."""
    faculty = _get_faculty_profile(request.user)
    assignments = FacultySubjectAssignment.objects.filter(faculty=faculty, is_active=True).select_related('class_section')
    classes = [a.class_section for a in assignments]

    at_risk_students = StudentProfile.objects.filter(
        class_section__in=classes,
        cached_risk_level__in=[RiskLevel.WARNING, RiskLevel.CRITICAL]
    ).select_related('user', 'class_section').order_by('cached_attendance_percentage')

    context = {
        'at_risk_students': at_risk_students,
        'active_nav': 'faculty_at_risk'
    }
    return render(request, 'faculty/at_risk.html', context)


@faculty_required
def faculty_leave_reviews_view(request):
    """Review Leave and On-Duty requests with approval/rejection comments."""
    faculty = _get_faculty_profile(request.user)
    assignments = FacultySubjectAssignment.objects.filter(faculty=faculty, is_active=True).select_related('class_section')
    classes = [a.class_section for a in assignments]

    if request.method == 'POST':
        leave_id = request.POST.get('leave_id')
        decision = request.POST.get('decision')  # 'APPROVED' or 'REJECTED'
        comment = request.POST.get('review_comment', '').strip()

        leave = get_object_or_404(LeaveRequest, id=leave_id, student__class_section__in=classes)
        leave.status = decision
        leave.reviewed_by = request.user
        leave.review_comment = comment
        leave.reviewed_at = timezone.now()
        leave.save()

        AuditLog.objects.create(
            user=request.user,
            action=f"LEAVE_REQUEST_{decision}",
            model_name="LeaveRequest",
            object_id=str(leave.id),
            details=f"Decision: {decision}. Comment: {comment}"
        )

        notify_leave_status_update(leave)
        messages.success(request, f"Leave request #{leave.id} has been {leave.get_status_display().lower()}.")
        return redirect('faculty_leave_reviews')

    pending_leaves = LeaveRequest.objects.filter(
        student__class_section__in=classes,
        status='PENDING'
    ).select_related('student__user', 'student__class_section').order_by('-created_at')

    past_leaves = LeaveRequest.objects.filter(
        student__class_section__in=classes
    ).exclude(status='PENDING').select_related('student__user', 'reviewed_by').order_by('-reviewed_at')[:20]

    context = {
        'pending_leaves': pending_leaves,
        'past_leaves': past_leaves,
        'active_nav': 'faculty_leave_reviews'
    }
    return render(request, 'faculty/leave_reviews.html', context)


@faculty_required
def faculty_correction_reviews_view(request):
    """Review student attendance correction requests."""
    faculty = _get_faculty_profile(request.user)
    assignments = FacultySubjectAssignment.objects.filter(faculty=faculty, is_active=True).select_related('subject')
    subjects = [a.subject for a in assignments]

    if request.method == 'POST':
        correction_id = request.POST.get('correction_id')
        decision = request.POST.get('decision')  # 'APPROVED' or 'REJECTED'
        comment = request.POST.get('review_comment', '').strip()

        correction = get_object_or_404(
            AttendanceCorrectionRequest,
            id=correction_id,
            attendance_record__session__subject__in=subjects
        )
        correction.status = decision
        correction.reviewed_by = request.user
        correction.review_comment = comment
        correction.reviewed_at = timezone.now()
        correction.save()

        # If approved, update attendance record
        if decision == 'APPROVED':
            rec = correction.attendance_record
            rec.status = correction.requested_status
            rec.remarks = f"Corrected via dispute #{correction.id}: {comment}"
            rec.save(update_fields=['status', 'remarks', 'updated_at'])
            # Recalculate metrics
            recalculate_and_sync_student_metrics(correction.student)

        AuditLog.objects.create(
            user=request.user,
            action=f"CORRECTION_REQUEST_{decision}",
            model_name="AttendanceCorrectionRequest",
            object_id=str(correction.id),
            details=f"Decision: {decision}. Requested status: {correction.requested_status}. Comment: {comment}"
        )

        notify_correction_status_update(correction)
        messages.success(request, f"Correction dispute #{correction.id} marked as {correction.get_status_display()}.")
        return redirect('faculty_correction_reviews')

    pending_corrections = AttendanceCorrectionRequest.objects.filter(
        attendance_record__session__subject__in=subjects,
        status='PENDING'
    ).select_related('student__user', 'attendance_record__session__subject').order_by('-created_at')

    past_corrections = AttendanceCorrectionRequest.objects.filter(
        attendance_record__session__subject__in=subjects
    ).exclude(status='PENDING').select_related('student__user', 'reviewed_by').order_by('-reviewed_at')[:20]

    context = {
        'pending_corrections': pending_corrections,
        'past_corrections': past_corrections,
        'active_nav': 'faculty_correction_reviews'
    }
    return render(request, 'faculty/correction_reviews.html', context)


@faculty_required
def faculty_export_class_view(request):
    """Exports class attendance sheet to Excel."""
    faculty = _get_faculty_profile(request.user)
    class_id = request.GET.get('class_id')
    subject_id = request.GET.get('subject_id')

    class_section = get_object_or_404(ClassSection, id=class_id)
    subject = get_object_or_404(Subject, id=subject_id)

    excel_stream = export_subject_attendance_excel(class_section, subject)
    response = HttpResponse(
        excel_stream.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"{subject.code}_{class_section.name}_attendance.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
