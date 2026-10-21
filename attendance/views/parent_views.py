"""
Parent Portal Views: Linked Wards Overview, Absence History, Absence Explanations,
and Alert Preference Configuration.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .auth_views import parent_required
from ..models import (
    ParentProfile, StudentParentRelation, StudentProfile, AttendanceRecord,
    ParentAbsenceExplanation, AttendanceStatus
)
from ..services.calculation_engine import get_student_overall_attendance, get_student_subject_attendance


def _get_parent_profile(user) -> ParentProfile:
    """Helper to retrieve parent profile or first available if superuser."""
    if hasattr(user, 'parent_profile'):
        return user.parent_profile
    return ParentProfile.objects.first()


@parent_required
def parent_dashboard_view(request):
    """Parent Portal Home: Overview of all linked children, attendance health, and recent alerts."""
    parent = _get_parent_profile(request.user)
    relations = StudentParentRelation.objects.filter(parent=parent).select_related('student__user', 'student__class_section')

    children_data = []
    for rel in relations:
        student = rel.student
        overall = get_student_overall_attendance(student)
        recent_absences = AttendanceRecord.objects.filter(
            student=student,
            status=AttendanceStatus.ABSENT,
            session__is_cancelled=False
        ).select_related('session__subject').order_by('-session__date', '-session__period_number')[:4]

        children_data.append({
            'student': student,
            'relationship': rel.get_relationship_type_display(),
            'overall': overall,
            'recent_absences': recent_absences
        })

    context = {
        'parent': parent,
        'children_data': children_data,
        'active_nav': 'parent_dashboard'
    }
    return render(request, 'parent/dashboard.html', context)


@parent_required
def parent_child_detail_view(request, student_id):
    """Detailed Subject-Wise Attendance Breakdown for a Specific Linked Child."""
    parent = _get_parent_profile(request.user)
    
    # Security: Verify that child is linked to this parent
    rel = StudentParentRelation.objects.filter(parent=parent, student_id=student_id).first()
    if not rel and not request.user.is_superuser:
        raise PermissionDenied("You are not authorized to view attendance records for this student.")

    student = get_object_or_404(StudentProfile, id=student_id)
    overall = get_student_overall_attendance(student)

    enrollments = student.enrollments.filter(is_active=True).select_related('subject')
    subject_details = []
    for enr in enrollments:
        data = get_student_subject_attendance(student, enr.subject)
        subject_details.append(data)

    context = {
        'student': student,
        'overall': overall,
        'subject_details': subject_details,
        'active_nav': 'parent_dashboard'
    }
    return render(request, 'parent/child_detail.html', context)


@parent_required
def parent_absence_history_view(request):
    """Log of all recorded unexcused absences for linked wards."""
    parent = _get_parent_profile(request.user)
    relations = StudentParentRelation.objects.filter(parent=parent).select_related('student')
    students = [rel.student for rel in relations]

    absences = AttendanceRecord.objects.filter(
        student__in=students,
        status=AttendanceStatus.ABSENT,
        session__is_cancelled=False
    ).select_related('student__user', 'session__subject', 'session__faculty__user').order_by('-session__date', '-session__period_number')

    context = {
        'absences': absences,
        'active_nav': 'parent_absence_history'
    }
    return render(request, 'parent/absence_history.html', context)


@parent_required
def parent_submit_explanation_view(request):
    """Submit formal absence justification letter to faculty."""
    parent = _get_parent_profile(request.user)
    relations = StudentParentRelation.objects.filter(parent=parent).select_related('student__user')
    students = [rel.student for rel in relations]

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        date_str = request.POST.get('date')
        reason = request.POST.get('reason', '').strip()

        # Security check: student must be in linked students
        student = get_object_or_404(StudentProfile, id=student_id, id__in=[s.id for s in students])

        if not (date_str and reason):
            messages.error(request, "Please fill in the date and reason for absence.")
        else:
            ParentAbsenceExplanation.objects.create(
                student=student,
                parent=parent,
                date=date_str,
                reason=reason
            )
            messages.success(request, f"Absence explanation for {student.roll_number} submitted to faculty.")
            return redirect('parent_submit_explanation')

    explanations = ParentAbsenceExplanation.objects.filter(parent=parent).select_related('student__user').order_by('-created_at')

    context = {
        'relations': relations,
        'explanations': explanations,
        'active_nav': 'parent_submit_explanation'
    }
    return render(request, 'parent/submit_explanation.html', context)


@parent_required
def parent_preferences_view(request):
    """Configure SMS, Email and Frequency Preferences for Attendance Alerts."""
    parent = _get_parent_profile(request.user)

    if request.method == 'POST':
        preference = request.POST.get('notification_preference', 'ALL')
        sms_enabled = 'sms_enabled' in request.POST
        email_enabled = 'email_enabled' in request.POST

        parent.notification_preference = preference
        parent.sms_enabled = sms_enabled
        parent.email_enabled = email_enabled
        parent.save(update_fields=['notification_preference', 'sms_enabled', 'email_enabled'])

        messages.success(request, "Your notification preferences have been updated.")
        return redirect('parent_preferences')

    context = {
        'parent': parent,
        'active_nav': 'parent_preferences'
    }
    return render(request, 'parent/preferences.html', context)
