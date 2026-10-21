"""
Automated Tests for Parent Alerts and Notification Delivery Channels.
"""

from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from attendance.models import (
    StudentProfile, ParentProfile, StudentParentRelation, ClassSection,
    Department, AcademicYear, Semester, Subject, AttendanceSession,
    AttendanceRecord, AttendanceStatus, Notification, NotificationDeliveryAttempt,
    DeliveryChannel, DeliveryStatus
)
from attendance.services.notification_service import notify_parents_of_absence


class NotificationsTestCase(TestCase):
    def setUp(self):
        # Structure
        self.year = AcademicYear.objects.create(name="2026-27", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.sem = Semester.objects.create(academic_year=self.year, number=1, name="Sem 1")
        self.dept = Department.objects.create(code="AIDS", name="AI & Data Science")
        self.sec = ClassSection.objects.create(department=self.dept, semester=self.sem, name="AIDS-A")
        self.subject = Subject.objects.create(code="AI101", name="Intro to AI", department=self.dept, semester=self.sem)

        # Users
        self.st_user = User.objects.create_user(username="test_st", password="password")
        self.student = StudentProfile.objects.create(user=self.st_user, roll_number="ST001", registration_number="REG001", class_section=self.sec)

        self.p_user = User.objects.create_user(username="test_parent", password="password", email="parent@example.com")
        self.parent = ParentProfile.objects.create(user=self.p_user, sms_enabled=True, email_enabled=True)
        StudentParentRelation.objects.create(student=self.student, parent=self.parent)

        # Session
        self.session = AttendanceSession.objects.create(
            class_section=self.sec,
            subject=self.subject,
            date=date(2026, 10, 20),
            period_number=1
        )

    def test_absence_creates_parent_notification_with_delivery_attempts(self):
        """Marking student absent dispatches notification and records in-app & simulated attempts."""
        record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student,
            status=AttendanceStatus.ABSENT
        )

        notifs = notify_parents_of_absence(record)
        self.assertEqual(len(notifs), 1)

        notif = notifs[0]
        self.assertEqual(notif.recipient, self.p_user)
        self.assertIn("marked absent in AI101", notif.title)

        attempts = NotificationDeliveryAttempt.objects.filter(notification=notif)
        channels = [a.channel for a in attempts]
        self.assertIn(DeliveryChannel.IN_APP, channels)
        self.assertIn(DeliveryChannel.SMS_SIMULATED, channels)

    def test_duplicate_submission_does_not_create_duplicate_alert(self):
        """Calling notify_parents_of_absence again for same record does not duplicate alerts."""
        record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student,
            status=AttendanceStatus.ABSENT
        )

        notifs_first = notify_parents_of_absence(record)
        self.assertEqual(len(notifs_first), 1)

        # Second invocation
        notifs_second = notify_parents_of_absence(record)
        self.assertEqual(len(notifs_second), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.p_user).count(), 1)
