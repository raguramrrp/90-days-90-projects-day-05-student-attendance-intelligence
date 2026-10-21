"""
Global context processors for role-aware application shell, notifications, and navigation badges.
"""

from .models import Notification, AttendanceCorrectionRequest, LeaveRequest, UserRole


def app_context(request):
    """Provides application-wide context variables for templates."""
    context = {
        'app_name': 'Student Attendance Intelligence',
        'app_version': '1.0.0',
        'current_role': None,
        'is_admin': False,
        'is_faculty': False,
        'is_student': False,
        'is_parent': False,
        'unread_notification_count': 0,
        'pending_correction_count': 0,
        'pending_leave_count': 0,
    }

    if request.user.is_authenticated:
        profile = getattr(request.user, 'profile', None)
        if profile:
            context['current_role'] = profile.role
            context['is_admin'] = profile.is_admin
            context['is_faculty'] = profile.is_faculty
            context['is_student'] = profile.is_student
            context['is_parent'] = profile.is_parent
        elif request.user.is_superuser:
            context['current_role'] = UserRole.ADMIN
            context['is_admin'] = True

        # Unread notifications
        try:
            context['unread_notification_count'] = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
        except Exception:
            context['unread_notification_count'] = 0

        # Faculty/Admin pending review badges
        if context['is_faculty'] or context['is_admin']:
            try:
                context['pending_correction_count'] = AttendanceCorrectionRequest.objects.filter(status='PENDING').count()
                context['pending_leave_count'] = LeaveRequest.objects.filter(status='PENDING').count()
            except Exception:
                pass

    return context
