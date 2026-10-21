"""
Management command to safely seed demonstration data for all 4 roles,
generating realistic historical sessions, varied risk categories,
parent links, leaves, correction requests, and notifications.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from attendance.models import (
    UserProfile, UserRole, Department, AcademicYear, Semester, ClassSection,
    FacultyProfile, StudentProfile, ParentProfile, StudentParentRelation,
    RelationshipType, Subject, FacultySubjectAssignment, StudentSubjectEnrollment,
    TimetableSession, AttendanceSession, AttendanceRecord, AttendanceStatus,
    SessionStatus, LeaveRequest, LeaveType, RequestStatus, AttendanceCorrectionRequest,
    AttendancePolicy, ParentAbsenceExplanation, Notification, NotificationCategory,
    NotificationDeliveryAttempt, DeliveryChannel, DeliveryStatus
)
from attendance.services.calculation_engine import recalculate_and_sync_student_metrics


class Command(BaseCommand):
    help = "Seeds reproducible, realistic demonstration data for Student Attendance Intelligence System."

    def handle(self, *args, **options):
        self.stdout.write("Initializing demonstration data seeding...")

        with transaction.atomic():
            # 1. Academic Structure
            acad_year, _ = AcademicYear.objects.get_or_create(
                name="2026-2027",
                defaults={'start_date': date(2026, 7, 1), 'end_date': date(2027, 5, 30), 'is_current': True}
            )

            sem7, _ = Semester.objects.get_or_create(
                academic_year=acad_year,
                number=7,
                defaults={'name': 'Semester 7 (Final Year Odd)', 'is_active': True}
            )

            dept_aids, _ = Department.objects.get_or_create(
                code="AIDS",
                defaults={'name': 'Artificial Intelligence & Data Science', 'description': 'B.Tech AI & Data Science'}
            )
            dept_cse, _ = Department.objects.get_or_create(
                code="CSE",
                defaults={'name': 'Computer Science & Engineering', 'description': 'B.Tech CSE'}
            )

            class_aids_a, _ = ClassSection.objects.get_or_create(
                department=dept_aids,
                semester=sem7,
                name="AIDS-IV-A",
                defaults={'batch_year': '2023-2027'}
            )
            class_aids_b, _ = ClassSection.objects.get_or_create(
                department=dept_aids,
                semester=sem7,
                name="AIDS-IV-B",
                defaults={'batch_year': '2023-2027'}
            )

            # 2. Institutional Attendance Policy
            AttendancePolicy.objects.get_or_create(
                department=None,
                defaults={
                    'min_attendance_percentage': 75.0,
                    'warning_threshold': 80.0,
                    'consecutive_absence_alert_count': 3,
                    'allow_correction_days': 7,
                    'calculation_mode': 'PERIOD_WEIGHTED'
                }
            )

            # 3. Subjects
            subj_dl, _ = Subject.objects.get_or_create(
                code="AI701",
                defaults={'name': 'Deep Learning & Neural Networks', 'department': dept_aids, 'semester': sem7, 'credits': 4, 'min_attendance_threshold': 75.0}
            )
            subj_nlp, _ = Subject.objects.get_or_create(
                code="AI702",
                defaults={'name': 'Natural Language Processing & LLMs', 'department': dept_aids, 'semester': sem7, 'credits': 4, 'min_attendance_threshold': 75.0}
            )
            subj_cv, _ = Subject.objects.get_or_create(
                code="AI703",
                defaults={'name': 'Computer Vision & Visual Perception', 'department': dept_aids, 'semester': sem7, 'credits': 3, 'min_attendance_threshold': 75.0}
            )
            subj_cloud, _ = Subject.objects.get_or_create(
                code="CS704",
                defaults={'name': 'Cloud Infrastructure & MLOps', 'department': dept_cse, 'semester': sem7, 'credits': 3, 'min_attendance_threshold': 75.0}
            )
            subj_rl, _ = Subject.objects.get_or_create(
                code="AI705",
                defaults={'name': 'Reinforcement Learning & Multi-Agent Systems', 'department': dept_aids, 'semester': sem7, 'credits': 3, 'min_attendance_threshold': 75.0}
            )

            all_subjects = [subj_dl, subj_nlp, subj_cv, subj_cloud, subj_rl]

            # 4. Administrator Account
            admin_user, _ = User.objects.get_or_create(
                username="admin",
                defaults={'email': 'admin@institution.edu', 'first_name': 'Institutional', 'last_name': 'Administrator', 'is_staff': True, 'is_superuser': True}
            )
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.update_or_create(
                user=admin_user,
                defaults={'role': UserRole.ADMIN, 'phone': '+91 9XXXX XX001', 'address': 'Academic Administrative Complex'}
            )

            # 5. Faculty Accounts
            faculty_data = [
                ('prof_ananya', 'Dr. Ananya', 'Sharma', 'prof.ananya@institution.edu', 'FAC001', 'Associate Professor', dept_aids),
                ('prof_karthik', 'Dr. Karthik', 'Raman', 'prof.karthik@institution.edu', 'FAC002', 'Assistant Professor', dept_aids),
            ]

            faculty_objs = {}
            for uname, fname, lname, email, empid, desig, dept in faculty_data:
                u, _ = User.objects.get_or_create(username=uname, defaults={'first_name': fname, 'last_name': lname, 'email': email})
                u.set_password('faculty123')
                u.save()
                UserProfile.objects.update_or_create(user=u, defaults={'role': UserRole.FACULTY, 'phone': '+91 9XXXX XX111'})
                f_prof, _ = FacultyProfile.objects.update_or_create(
                    user=u,
                    defaults={'employee_id': empid, 'department': dept, 'designation': desig, 'qualification': 'Ph.D in AI'}
                )
                faculty_objs[uname] = f_prof

            # Assign courses
            FacultySubjectAssignment.objects.get_or_create(
                faculty=faculty_objs['prof_ananya'], subject=subj_dl, class_section=class_aids_a, academic_year=acad_year
            )
            FacultySubjectAssignment.objects.get_or_create(
                faculty=faculty_objs['prof_ananya'], subject=subj_nlp, class_section=class_aids_a, academic_year=acad_year
            )
            FacultySubjectAssignment.objects.get_or_create(
                faculty=faculty_objs['prof_karthik'], subject=subj_cv, class_section=class_aids_a, academic_year=acad_year
            )
            FacultySubjectAssignment.objects.get_or_create(
                faculty=faculty_objs['prof_karthik'], subject=subj_cloud, class_section=class_aids_a, academic_year=acad_year
            )

            # 6. Student Accounts (Configured with specific target attendance profiles)
            # 23ai001: Safe (~92%)
            # 23ai008: Warning (~77%)
            # 23ai014: Critical (~68%)
            # 23ai020: Safe (~84%)
            # 23ai025: Warning with improving trend (~79%)
            # 23ai030: Perfect (100%)
            student_configs = [
                ('23ai001', 'Aarav', 'Sharma', '23ai001@institution.edu', 'REG2023001', class_aids_a, 0.92),
                ('23ai008', 'Diya', 'Mehta', '23ai008@institution.edu', 'REG2023008', class_aids_a, 0.77),
                ('23ai014', 'Rohan', 'Verma', '23ai014@institution.edu', 'REG2023014', class_aids_a, 0.68),
                ('23ai020', 'Vikram', 'Rao', '23ai020@institution.edu', 'REG2023020', class_aids_a, 0.84),
                ('23ai025', 'Priya', 'Nair', '23ai025@institution.edu', 'REG2023025', class_aids_a, 0.79),
                ('23ai030', 'Siddharth', 'Iyer', '23ai030@institution.edu', 'REG2023030', class_aids_a, 1.00),
            ]

            student_profiles = {}
            for uname, fname, lname, email, regno, c_sec, target_rate in student_configs:
                u, _ = User.objects.get_or_create(username=uname, defaults={'first_name': fname, 'last_name': lname, 'email': email})
                u.set_password('student123')
                u.save()
                UserProfile.objects.update_or_create(user=u, defaults={'role': UserRole.STUDENT, 'phone': '+91 9XXXX XX345'})
                st_prof, _ = StudentProfile.objects.update_or_create(
                    user=u,
                    defaults={
                        'roll_number': uname.upper(),
                        'registration_number': regno,
                        'class_section': c_sec,
                        'emergency_contact': '+91 9XXXX XX999'
                    }
                )
                student_profiles[uname] = (st_prof, target_rate)

                # Enroll in subjects
                for sub in all_subjects:
                    StudentSubjectEnrollment.objects.get_or_create(
                        student=st_prof, subject=sub, class_section=c_sec, defaults={'is_active': True}
                    )

            # 7. Parent Accounts & Linkage
            parent_configs = [
                ('parent_sharma', 'Mr. Rajesh', 'Sharma', 'parent.sharma@gmail.com', '23ai001', RelationshipType.FATHER),
                ('parent_mehta', 'Mrs. Kavita', 'Mehta', 'parent.mehta@gmail.com', '23ai008', RelationshipType.MOTHER),
                ('parent_verma', 'Mrs. Sunita', 'Verma', 'parent.verma@gmail.com', '23ai014', RelationshipType.MOTHER),
            ]

            for puname, pfname, plname, pemail, child_roll, rel_type in parent_configs:
                pu, _ = User.objects.get_or_create(username=puname, defaults={'first_name': pfname, 'last_name': plname, 'email': pemail})
                pu.set_password('parent123')
                pu.save()
                UserProfile.objects.update_or_create(user=pu, defaults={'role': UserRole.PARENT, 'phone': '+91 9XXXX XX321'})
                p_prof, _ = ParentProfile.objects.update_or_create(
                    user=pu,
                    defaults={'occupation': 'Engineer', 'notification_preference': 'ALL', 'sms_enabled': True, 'email_enabled': True}
                )
                target_student = student_profiles[child_roll][0]
                StudentParentRelation.objects.get_or_create(
                    student=target_student, parent=p_prof,
                    defaults={'relationship_type': rel_type, 'is_primary': True}
                )

            # 8. Timetable
            tt_schedule = [
                (0, 1, subj_dl, faculty_objs['prof_ananya']),
                (0, 2, subj_nlp, faculty_objs['prof_ananya']),
                (0, 3, subj_cv, faculty_objs['prof_karthik']),
                (1, 1, subj_cloud, faculty_objs['prof_karthik']),
                (1, 2, subj_dl, faculty_objs['prof_ananya']),
                (2, 1, subj_nlp, faculty_objs['prof_ananya']),
                (2, 2, subj_rl, faculty_objs['prof_karthik']),
                (3, 1, subj_cv, faculty_objs['prof_karthik']),
                (3, 2, subj_cloud, faculty_objs['prof_karthik']),
                (4, 1, subj_dl, faculty_objs['prof_ananya']),
                (4, 2, subj_rl, faculty_objs['prof_karthik']),
            ]

            for dow, pnum, subj, fac in tt_schedule:
                TimetableSession.objects.get_or_create(
                    class_section=class_aids_a,
                    day_of_week=dow,
                    period_number=pnum,
                    defaults={
                        'subject': subj,
                        'faculty': fac,
                        'start_time': '09:00',
                        'end_time': '10:00',
                        'room_number': 'Lab-3B'
                    }
                )

            # 9. Historical Attendance Sessions (20 past days, 2 periods per day)
            today = timezone.now().date()
            import random
            random.seed(42)

            session_count = 0
            for days_back in range(21, 0, -1):
                sess_date = today - timedelta(days=days_back)
                # Skip Sundays (6)
                if sess_date.weekday() == 6:
                    continue

                for p_idx in [1, 2]:
                    chosen_sub = all_subjects[(days_back + p_idx) % len(all_subjects)]
                    fac = faculty_objs['prof_ananya'] if p_idx == 1 else faculty_objs['prof_karthik']

                    session, _ = AttendanceSession.objects.get_or_create(
                        class_section=class_aids_a,
                        subject=chosen_sub,
                        date=sess_date,
                        period_number=p_idx,
                        defaults={
                            'faculty': fac,
                            'status': SessionStatus.SUBMITTED,
                            'topic_covered': f"{chosen_sub.code} Lecture #{days_back}.{p_idx}",
                            'submitted_by': fac.user
                        }
                    )
                    session_count += 1

                    for roll, (st_prof, target_rate) in student_profiles.items():
                        # Determine status based on target rate
                        rnd = random.random()
                        if rnd <= target_rate:
                            status_val = AttendanceStatus.PRESENT
                            remarks = ""
                        elif rnd <= target_rate + 0.05:
                            status_val = AttendanceStatus.EXCUSED
                            remarks = "Approved Academic On-Duty"
                        else:
                            status_val = AttendanceStatus.ABSENT
                            remarks = "Uninformed Absence"

                        AttendanceRecord.objects.get_or_create(
                            session=session,
                            student=st_prof,
                            defaults={'status': status_val, 'remarks': remarks, 'recorded_by': fac.user}
                        )

            # 10. Sample Leave & OD Requests
            st_aarav = student_profiles['23ai001'][0]
            st_rohan = student_profiles['23ai014'][0]
            st_diya = student_profiles['23ai008'][0]

            LeaveRequest.objects.get_or_create(
                student=st_aarav,
                request_type=LeaveType.ON_DUTY,
                start_date=today - timedelta(days=5),
                end_date=today - timedelta(days=4),
                defaults={
                    'reason': 'Selected for Smart India Hackathon Grand Finale at IIT Madras.',
                    'status': RequestStatus.APPROVED,
                    'reviewed_by': faculty_objs['prof_ananya'].user,
                    'review_comment': 'Granted OD permission. Excellent opportunity for institution.',
                    'reviewed_at': timezone.now() - timedelta(days=4)
                }
            )

            LeaveRequest.objects.get_or_create(
                student=st_rohan,
                request_type=LeaveType.LEAVE,
                start_date=today + timedelta(days=1),
                end_date=today + timedelta(days=3),
                defaults={
                    'reason': 'Medical leave due to viral fever diagnosed by physician.',
                    'status': RequestStatus.PENDING
                }
            )

            # 11. Sample Correction Dispute
            recent_absent_rec = AttendanceRecord.objects.filter(
                student=st_rohan, status=AttendanceStatus.ABSENT
            ).first()

            if recent_absent_rec:
                AttendanceCorrectionRequest.objects.get_or_create(
                    attendance_record=recent_absent_rec,
                    student=st_rohan,
                    defaults={
                        'requested_status': AttendanceStatus.PRESENT,
                        'reason': 'Entered lecture hall at 09:05 AM after late bus transit; missed first 5-minute roll call.',
                        'status': RequestStatus.PENDING
                    }
                )

            # 12. Sample Parent Absence Explanation
            p_verma = ParentProfile.objects.filter(user__username='parent_verma').first()
            if p_verma:
                ParentAbsenceExplanation.objects.get_or_create(
                    student=st_rohan,
                    parent=p_verma,
                    date=today - timedelta(days=2),
                    defaults={
                        'reason': 'Rohan was indisposed due to severe fever. Medical prescription will be submitted.',
                        'status': 'SUBMITTED'
                    }
                )

            # 13. Sample Notifications and Simulation Logs
            notif_absence = Notification.objects.create(
                recipient=p_verma.user,
                student=st_rohan,
                title=f"Absence Notice: {st_rohan.user.get_full_name()} marked absent",
                message=f"Dear Parent, your ward {st_rohan.user.get_full_name()} ({st_rohan.roll_number}) was recorded ABSENT for Period 1 in AI701 on {today - timedelta(days=2)}. Please inspect the portal.",
                category=NotificationCategory.ABSENCE,
                action_url="/parent-portal/absences/"
            )
            NotificationDeliveryAttempt.objects.create(
                notification=notif_absence,
                channel=DeliveryChannel.IN_APP,
                status=DeliveryStatus.SENT,
                provider_message_id=f"inapp-{notif_absence.id}"
            )
            NotificationDeliveryAttempt.objects.create(
                notification=notif_absence,
                channel=DeliveryChannel.SMS_SIMULATED,
                status=DeliveryStatus.SIMULATED,
                provider_message_id="sim-sms-demo-9901",
                error_message="Sandbox simulation: SMS gateway mock dispatched successfully to registered mobile number."
            )

            notif_risk = Notification.objects.create(
                recipient=st_rohan.user,
                student=st_rohan,
                title="Early Warning Alert: Attendance Critical Status",
                message=f"Attendance Intelligence Warning: Your overall attendance is currently below 75%. Use the Recovery Simulator immediately.",
                category=NotificationCategory.RISK_CRITICAL,
                action_url="/student-portal/simulator/"
            )
            NotificationDeliveryAttempt.objects.create(
                notification=notif_risk,
                channel=DeliveryChannel.IN_APP,
                status=DeliveryStatus.SENT,
                provider_message_id=f"inapp-{notif_risk.id}"
            )

            # 14. Recalculate Metrics for all Students
            self.stdout.write("Synchronizing student attendance metrics & risk levels...")
            for uname, (st_prof, _) in student_profiles.items():
                recalculate_and_sync_student_metrics(st_prof)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded demo data: {session_count} attendance sessions, "
            f"{len(student_profiles)} students across Safe, Warning, and Critical statuses, "
            f"parents, faculty, timetable, leaves, disputes, and notifications."
        ))
