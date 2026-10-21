"""
Automated Tests for Leave Requests and Attendance Correction Disputes.
"""

from datetime import date
from django.test import TestCase
from django.contrib.auth.models import User
from attendance.models import (
    StudentProfile, FacultyProfile, ClassSection, Department, AcademicYear,
    Semester, Subject, AttendanceSession, AttendanceRecord, AttendanceStatus,
    LeaveRequest, LeaveType, RequestStatus, AttendanceCorrectionRequest, AuditLog
)
from attendance.services.calculation_engine import recalculate_and_sync_student_metrics


class LeaveAndCorrectionsTestCase(TestCase):
    def setUp(self):
        self.year = AcademicYear.objects.create(name="2026-27", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
        self.sem = Semester.objects.create(academic_year=self.year, number=1, name="Sem 1")
        self.dept = Department.objects.create(code="AIDS", name="AI & Data Science")
        self.sec = ClassSection.objects.create(department=self.dept, semester=self.sem, name="AIDS-A")
        self.subject = Subject.objects.create(code="AI101", name="Intro to AI", department=self.dept, semester=self.sem)

        self.st_user = User.objects.create_user(username="test_st", password="password")
        self.student = StudentProfile.objects.create(user=self.st_user, roll_number="ST001", registration_number="REG001", class_section=self.sec)

        self.fac_user = User.objects.create_user(username="test_fac", password="password")
        self.faculty = FacultyProfile.objects.create(user=self.fac_user, employee_id="FAC001", department=self.dept)

        self.session = AttendanceSession.objects.create(
            class_section=self.sec, subject=self.subject, date=date(2026, 10, 20), period_number=1, faculty=self.faculty
        )

    def test_leave_request_workflow(self):
        """Student submits leave request; faculty reviews and approves."""
        leave = LeaveRequest.objects.create(
            student=self.student,
            request_type=LeaveType.ON_DUTY,
            start_date=date(2026, 10, 21),
            end_date=date(2026, 10, 22),
            reason="Representing university in coding championship."
        )
        self.assertEqual(leave.status, RequestStatus.PENDING)

        # Faculty approval
        leave.status = RequestStatus.APPROVED
        leave.reviewed_by = self.fac_user
        leave.review_comment = "Granted. Good luck."
        leave.save()

        self.assertEqual(LeaveRequest.objects.get(id=leave.id).status, RequestStatus.APPROVED)

    def test_correction_request_approval_updates_attendance(self):
        """Approved attendance correction changes record status and recalculates student metrics."""
        record = AttendanceRecord.objects.create(
            session=self.session,
            student=self.student,
            status=AttendanceStatus.ABSENT
        )
        recalculate_and_sync_student_metrics(self.student)
        self.assertEqual(self.student.cached_attendance_percentage, 0.0)

        correction = AttendanceCorrectionRequest.objects.create(
            attendance_record=record,
            student=self.student,
            requested_status=AttendanceStatus.PRESENT,
            reason="Was present in 2nd row; roll call discrepancy."
        )
        self.assertEqual(correction.status, RequestStatus.PENDING)

        # Approve dispute
        correction.status = RequestStatus.APPROVED
        correction.reviewed_by = self.fac_user
        correction.review_comment = "Verified via hall camera."
        correction.save()

        # Update actual record as service does
        record.status = correction.requested_status
        record.remarks = "Corrected via dispute"
        record.save()

        recalculate_and_sync_student_metrics(self.student)
        self.assertEqual(self.student.cached_attendance_percentage, 100.0)
