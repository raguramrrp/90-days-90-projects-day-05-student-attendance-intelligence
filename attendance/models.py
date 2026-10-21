"""
Database models for Student Attendance Intelligence & Early Warning System.
Normalized, constrained, indexed, and audited.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrator'
    FACULTY = 'FACULTY', 'Faculty'
    STUDENT = 'STUDENT', 'Student'
    PARENT = 'PARENT', 'Parent'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.STUDENT, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN or self.user.is_superuser

    @property
    def is_faculty(self):
        return self.role == UserRole.FACULTY

    @property
    def is_student(self):
        return self.role == UserRole.STUDENT

    @property
    def is_parent(self):
        return self.role == UserRole.PARENT


class Department(models.Model):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)  # e.g. "2026-2027"
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Semester(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name='semesters')
    number = models.PositiveSmallIntegerField()  # 1 to 8
    name = models.CharField(max_length=60)  # e.g. "Semester 7 (Odd)"
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['academic_year', 'number']
        unique_together = ('academic_year', 'number')

    def __str__(self):
        return f"{self.name} - {self.academic_year.name}"


class ClassSection(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='class_sections')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='class_sections')
    name = models.CharField(max_length=60)  # e.g. "AIDS-IV-A"
    batch_year = models.CharField(max_length=20, default="2023-2027")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['department', 'name']
        unique_together = ('department', 'semester', 'name')

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class FacultyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='faculty_profile')
    employee_id = models.CharField(max_length=30, unique=True, db_index=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='faculty_members')
    designation = models.CharField(max_length=100, default="Assistant Professor")
    qualification = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.employee_id})"


class RiskLevel(models.TextChoices):
    SAFE = 'SAFE', 'Safe'
    WARNING = 'WARNING', 'Warning'
    CRITICAL = 'CRITICAL', 'Critical'


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    roll_number = models.CharField(max_length=30, unique=True, db_index=True)
    registration_number = models.CharField(max_length=30, unique=True, db_index=True)
    class_section = models.ForeignKey(ClassSection, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    date_of_birth = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    
    # Cached metrics for fast queries (updated synchronously via calculation service)
    cached_attendance_percentage = models.FloatField(default=100.0)
    cached_risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.SAFE, db_index=True)
    last_calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['roll_number']

    def __str__(self):
        return f"{self.roll_number} - {self.user.get_full_name() or self.user.username}"


class ParentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    occupation = models.CharField(max_length=100, blank=True)
    notification_preference = models.CharField(
        max_length=20,
        choices=[
            ('ALL', 'All Notifications (Absences & Alerts)'),
            ('ALERTS_ONLY', 'Risk Warnings & Alerts Only'),
            ('DAILY_DIGEST', 'Daily Summary Only'),
        ],
        default='ALL'
    )
    sms_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (Parent)"


class RelationshipType(models.TextChoices):
    FATHER = 'FATHER', 'Father'
    MOTHER = 'MOTHER', 'Mother'
    GUARDIAN = 'GUARDIAN', 'Guardian'


class StudentParentRelation(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parent_relations')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='student_relations')
    relationship_type = models.CharField(max_length=20, choices=RelationshipType.choices, default=RelationshipType.FATHER)
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'parent')

    def __str__(self):
        return f"{self.parent} -> {self.student} ({self.get_relationship_type_display()})"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='subjects')
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='subjects')
    credits = models.PositiveSmallIntegerField(default=3)
    min_attendance_threshold = models.FloatField(default=75.0)
    is_elective = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"


class FacultySubjectAssignment(models.Model):
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.CASCADE, related_name='teaching_assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='faculty_assignments')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='subject_assignments')
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('faculty', 'subject', 'class_section', 'academic_year')

    def __str__(self):
        return f"{self.faculty} - {self.subject.code} ({self.class_section.name})"


class StudentSubjectEnrollment(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='enrollments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='student_enrollments')
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='student_enrollments')
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student.roll_number} - {self.subject.code}"


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'


class TimetableSession(models.Model):
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='timetable_entries')
    day_of_week = models.PositiveSmallIntegerField(choices=DayOfWeek.choices)
    period_number = models.PositiveSmallIntegerField()  # 1 to 8
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_number = models.CharField(max_length=30, blank=True)

    class Meta:
        ordering = ['day_of_week', 'period_number']
        unique_together = ('class_section', 'day_of_week', 'period_number')

    def __str__(self):
        return f"{self.class_section.name} | {self.get_day_of_week_display()} P{self.period_number} - {self.subject.code}"


class SessionStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    FINALIZED = 'FINALIZED', 'Finalized'


class AttendanceSession(models.Model):
    class_section = models.ForeignKey(ClassSection, on_delete=models.CASCADE, related_name='attendance_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='attendance_sessions')
    faculty = models.ForeignKey(FacultyProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='marked_sessions')
    date = models.DateField(db_index=True)
    period_number = models.PositiveSmallIntegerField()
    topic_covered = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=SessionStatus.choices, default=SessionStatus.SUBMITTED)
    is_cancelled = models.BooleanField(default=False)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'period_number']
        unique_together = ('class_section', 'subject', 'date', 'period_number')
        indexes = [
            models.Index(fields=['class_section', 'date']),
            models.Index(fields=['subject', 'date']),
        ]

    def __str__(self):
        return f"{self.subject.code} - {self.class_section.name} | {self.date} (P{self.period_number})"


class AttendanceStatus(models.TextChoices):
    PRESENT = 'PRESENT', 'Present'
    ABSENT = 'ABSENT', 'Absent'
    EXCUSED = 'EXCUSED', 'Approved On-Duty / Excused'


class AttendanceRecord(models.Model):
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attendance_records')
    status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    remarks = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recorded_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['session', 'status']),
        ]

    def __str__(self):
        return f"{self.student.roll_number} - {self.session.subject.code} ({self.session.date} P{self.session.period_number}): {self.get_status_display()}"


class RequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Review'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'


class AttendanceCorrectionRequest(models.Model):
    attendance_record = models.ForeignKey(AttendanceRecord, on_delete=models.CASCADE, related_name='correction_requests')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='correction_requests')
    requested_status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_corrections')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Correction #{self.pk}: {self.student.roll_number} -> {self.get_requested_status_display()} ({self.get_status_display()})"


class LeaveType(models.TextChoices):
    LEAVE = 'LEAVE', 'Medical / Personal Leave'
    ON_DUTY = 'ON_DUTY', 'On-Duty (Hackathon/Symposium/Sports)'
    INTERNSHIP = 'INTERNSHIP', 'Internship Permission'


class LeaveRequest(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='leave_requests')
    request_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.LEAVE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    supporting_document = models.FileField(upload_to='leave_documents/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.PENDING, db_index=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves')
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_request_type_display()} #{self.pk}: {self.student.roll_number} ({self.start_date} to {self.end_date})"


class ParentAbsenceExplanation(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parent_explanations')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='explanations_submitted')
    date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default='SUBMITTED', choices=[('SUBMITTED', 'Submitted'), ('ACKNOWLEDGED', 'Acknowledged by Faculty')])
    faculty_remarks = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_explanations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Explanation for {self.student.roll_number} on {self.date} by {self.parent}"


class NotificationCategory(models.TextChoices):
    ABSENCE = 'ABSENCE', 'Period Absence Alert'
    RISK_WARNING = 'RISK_WARNING', 'Attendance Warning'
    RISK_CRITICAL = 'RISK_CRITICAL', 'Attendance Critical Alert'
    LEAVE_STATUS = 'LEAVE_STATUS', 'Leave / OD Update'
    CORRECTION_STATUS = 'CORRECTION_STATUS', 'Attendance Correction Update'
    SYSTEM = 'SYSTEM', 'Institutional Notice'


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='related_notifications')
    title = models.CharField(max_length=160)
    message = models.TextField()
    category = models.CharField(max_length=30, choices=NotificationCategory.choices, default=NotificationCategory.SYSTEM)
    is_read = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"


class DeliveryChannel(models.TextChoices):
    IN_APP = 'IN_APP', 'In-App Notification'
    EMAIL = 'EMAIL', 'Email Delivery'
    SMS_SIMULATED = 'SMS_SIMULATED', 'Simulated SMS'
    WHATSAPP_SIMULATED = 'WHATSAPP_SIMULATED', 'Simulated WhatsApp'


class DeliveryStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SENT = 'SENT', 'Sent / Delivered'
    FAILED = 'FAILED', 'Failed'
    SIMULATED = 'SIMULATED', 'Simulated Delivery (Local Sandbox)'


class NotificationDeliveryAttempt(models.Model):
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='delivery_attempts')
    channel = models.CharField(max_length=30, choices=DeliveryChannel.choices, default=DeliveryChannel.IN_APP)
    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.SIMULATED)
    provider_message_id = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    attempt_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempt_time']

    def __str__(self):
        return f"Attempt #{self.pk} for Notif {self.notification_id} [{self.channel}]: {self.status}"


class AttendancePolicy(models.Model):
    department = models.OneToOneField(Department, on_delete=models.CASCADE, null=True, blank=True, related_name='attendance_policy')
    min_attendance_percentage = models.FloatField(default=75.0)
    warning_threshold = models.FloatField(default=80.0)
    consecutive_absence_alert_count = models.PositiveSmallIntegerField(default=3)
    allow_correction_days = models.PositiveSmallIntegerField(default=7)
    calculation_mode = models.CharField(
        max_length=30,
        default='PERIOD_WEIGHTED',
        choices=[
            ('PERIOD_WEIGHTED', 'Individual Period Sessions (Standard)'),
            ('DAY_PROPORTIONAL', 'Day Proportional'),
        ]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        dept_name = self.department.code if self.department else "Global Institutional Default"
        return f"Policy [{dept_name}]: Min {self.min_attendance_percentage}%, Warning {self.warning_threshold}%"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_entries')
    action = models.CharField(max_length=60, db_index=True)
    model_name = models.CharField(max_length=60)
    object_id = models.CharField(max_length=60, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {self.user.username if self.user else 'System'} - {self.action} on {self.model_name} #{self.object_id}"
