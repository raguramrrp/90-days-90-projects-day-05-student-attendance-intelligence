"""
Immediate Notification Engine & Delivery Abstraction.
Handles database-backed in-app alerts, email triggers, and simulated SMS/WhatsApp dispatch
with duplicate prevention and delivery audit logging.
"""

import uuid
from typing import List, Optional
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from ..models import (
    Notification, NotificationCategory, NotificationDeliveryAttempt,
    DeliveryChannel, DeliveryStatus, StudentProfile, AttendanceRecord,
    AttendanceSession, StudentParentRelation, User, UserRole, LeaveRequest,
    AttendanceCorrectionRequest
)


def dispatch_notification(
    recipient: User,
    title: str,
    message: str,
    category: str = NotificationCategory.SYSTEM,
    student: Optional[StudentProfile] = None,
    action_url: str = "",
    channels: Optional[List[str]] = None
) -> Notification:
    """
    Creates a database-backed Notification and records delivery attempts
    across requested channels (IN_APP, EMAIL, SMS_SIMULATED, WHATSAPP_SIMULATED).
    """
    if channels is None:
        channels = [DeliveryChannel.IN_APP]

    # Create primary database record
    notification = Notification.objects.create(
        recipient=recipient,
        student=student,
        title=title,
        message=message,
        category=category,
        action_url=action_url,
        is_read=False
    )

    # In-App is always delivered immediately to database
    NotificationDeliveryAttempt.objects.create(
        notification=notification,
        channel=DeliveryChannel.IN_APP,
        status=DeliveryStatus.SENT,
        provider_message_id=f"inapp-{notification.id}"
    )

    # Optional Email Channel
    if DeliveryChannel.EMAIL in channels:
        _deliver_email(notification, recipient, title, message)

    # Simulated SMS Channel
    if DeliveryChannel.SMS_SIMULATED in channels:
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=DeliveryChannel.SMS_SIMULATED,
            status=DeliveryStatus.SIMULATED,
            provider_message_id=f"sim-sms-{uuid.uuid4().hex[:12]}",
            error_message="Sandbox simulation: SMS gateway mock dispatched successfully to registered mobile number."
        )

    # Simulated WhatsApp Channel
    if DeliveryChannel.WHATSAPP_SIMULATED in channels:
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=DeliveryChannel.WHATSAPP_SIMULATED,
            status=DeliveryStatus.SIMULATED,
            provider_message_id=f"sim-wa-{uuid.uuid4().hex[:12]}",
            error_message="Sandbox simulation: WhatsApp template message mock dispatched via educational webhook."
        )

    return notification


def _deliver_email(notification: Notification, recipient: User, title: str, message: str):
    """Sends email or records simulated/failed attempt."""
    recipient_email = recipient.email
    if not recipient_email:
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=DeliveryChannel.EMAIL,
            status=DeliveryStatus.FAILED,
            error_message="Recipient user profile does not have an active email address registered."
        )
        return

    try:
        if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
            send_mail(
                subject=f"[Attendance Alert] {title}",
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False
            )
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                channel=DeliveryChannel.EMAIL,
                status=DeliveryStatus.SENT,
                provider_message_id=f"smtp-{uuid.uuid4().hex[:12]}"
            )
        else:
            # Simulated console / development mode
            NotificationDeliveryAttempt.objects.create(
                notification=notification,
                channel=DeliveryChannel.EMAIL,
                status=DeliveryStatus.SIMULATED,
                provider_message_id=f"sim-email-{uuid.uuid4().hex[:12]}",
                error_message="Simulated email: SMTP credentials not set in .env; email logged to local sandbox."
            )
    except Exception as exc:
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            channel=DeliveryChannel.EMAIL,
            status=DeliveryStatus.FAILED,
            error_message=str(exc)
        )


def notify_parents_of_absence(record: AttendanceRecord) -> List[Notification]:
    """
    Triggers immediate absence notifications to all linked parents of the student.
    Prevents duplicate notifications for the exact same session attendance record.
    """
    if record.status != 'ABSENT':
        return []

    student = record.student
    session = record.session
    subject = session.subject

    # Check for existing notification to avoid spamming on page refresh/re-submit
    existing_marker = f"absence-rec-{record.id}"
    if Notification.objects.filter(student=student, message__contains=existing_marker).exists():
        return []

    # Find linked parents
    relations = StudentParentRelation.objects.filter(student=student).select_related('parent__user')
    created_notifications = []

    for rel in relations:
        parent_user = rel.parent.user
        student_name = student.user.get_full_name() or student.roll_number
        date_str = session.date.strftime("%d %b %Y")
        
        title = f"Absence Notice: {student_name} marked absent in {subject.code}"
        message = (
            f"Dear Parent, your ward {student_name} ({student.roll_number}) was recorded ABSENT for "
            f"Period {session.period_number} in {subject.name} ({subject.code}) on {date_str}. "
            f"Please check the parent portal for details or submit an absence explanation if necessary. "
            f"[{existing_marker}]"
        )
        action_url = reverse('parent_absence_history')

        channels = [DeliveryChannel.IN_APP]
        if rel.parent.email_enabled:
            channels.append(DeliveryChannel.EMAIL)
        if rel.parent.sms_enabled:
            channels.append(DeliveryChannel.SMS_SIMULATED)
            channels.append(DeliveryChannel.WHATSAPP_SIMULATED)

        notif = dispatch_notification(
            recipient=parent_user,
            title=title,
            message=message,
            category=NotificationCategory.ABSENCE,
            student=student,
            action_url=action_url,
            channels=channels
        )
        created_notifications.append(notif)

    return created_notifications


def notify_risk_status_change(student: StudentProfile, old_risk: str, new_risk: str) -> None:
    """Notifies student and linked parents when student crosses into WARNING or CRITICAL."""
    if new_risk not in ('WARNING', 'CRITICAL') or new_risk == old_risk:
        return

    student_name = student.user.get_full_name() or student.roll_number
    category = NotificationCategory.RISK_CRITICAL if new_risk == 'CRITICAL' else NotificationCategory.RISK_WARNING
    
    title = f"Attendance Risk Alert: {new_risk.title()} Status for {student_name}"
    message = (
        f"Attendance Intelligence Warning: {student_name} ({student.roll_number}) has reached {new_risk} status "
        f"with current attendance at {student.cached_attendance_percentage}%. "
        f"Please review the Attendance Recovery Simulator immediately to restore eligibility."
    )

    # 1. Notify Student
    dispatch_notification(
        recipient=student.user,
        title=title,
        message=message,
        category=category,
        student=student,
        action_url=reverse('student_attendance_simulator'),
        channels=[DeliveryChannel.IN_APP, DeliveryChannel.EMAIL]
    )

    # 2. Notify Parents
    relations = StudentParentRelation.objects.filter(student=student).select_related('parent__user')
    for rel in relations:
        dispatch_notification(
            recipient=rel.parent.user,
            title=title,
            message=message,
            category=category,
            student=student,
            action_url=reverse('parent_dashboard'),
            channels=[DeliveryChannel.IN_APP, DeliveryChannel.EMAIL, DeliveryChannel.SMS_SIMULATED]
        )


def notify_leave_status_update(leave: LeaveRequest) -> None:
    """Notifies student when leave/OD request is approved or rejected."""
    student_user = leave.student.user
    title = f"Leave Request #{leave.id} {leave.get_status_display()}"
    comment_text = f" Remark: '{leave.review_comment}'" if leave.review_comment else ""
    message = (
        f"Your {leave.get_request_type_display()} request from {leave.start_date} to {leave.end_date} "
        f"has been marked as {leave.get_status_display()} by faculty.{comment_text}"
    )
    dispatch_notification(
        recipient=student_user,
        title=title,
        message=message,
        category=NotificationCategory.LEAVE_STATUS,
        student=leave.student,
        action_url=reverse('student_leave_requests'),
        channels=[DeliveryChannel.IN_APP, DeliveryChannel.EMAIL]
    )


def notify_correction_status_update(correction: AttendanceCorrectionRequest) -> None:
    """Notifies student when attendance correction is approved or rejected."""
    student_user = correction.student.user
    title = f"Correction Request #{correction.id} {correction.get_status_display()}"
    comment_text = f" Remark: '{correction.review_comment}'" if correction.review_comment else ""
    message = (
        f"Your correction dispute for {correction.attendance_record.session.subject.code} "
        f"on {correction.attendance_record.session.date} has been {correction.get_status_display()}.{comment_text}"
    )
    dispatch_notification(
        recipient=student_user,
        title=title,
        message=message,
        category=NotificationCategory.CORRECTION_STATUS,
        student=correction.student,
        action_url=reverse('student_correction_requests'),
        channels=[DeliveryChannel.IN_APP, DeliveryChannel.EMAIL]
    )
