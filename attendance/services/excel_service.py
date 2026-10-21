"""
Excel Import & Export Service using openpyxl and pandas.
Provides template generation, row-level validation, preview before commit,
formula-injection sanitized exports, and audit logging.
"""

import io
from datetime import datetime, date
from typing import Dict, Any, List, Tuple
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from django.db import transaction
from django.utils import timezone
from ..models import (
    StudentProfile, Subject, ClassSection, AttendanceSession, AttendanceRecord,
    AttendanceStatus, SessionStatus, User, AuditLog, NotificationDeliveryAttempt
)
from .calculation_engine import recalculate_and_sync_student_metrics
from .notification_service import notify_parents_of_absence


def sanitize_cell_value(val: Any) -> Any:
    """Prevents spreadsheet formula injection by escaping leading control characters."""
    if isinstance(val, str) and val.startswith(('=', '+', '-', '@')):
        return "'" + val
    return val


def mask_phone_value(val: Any) -> str:
    """Masks phone numbers for privacy protection in exported reports."""
    if not val or val == "N/A":
        return "-"
    val_str = str(val).strip()
    if len(val_str) > 8:
        return f"{val_str[:6]}****{val_str[-3:]}"
    elif len(val_str) > 4:
        return f"{val_str[:2]}****{val_str[-2:]}"
    return "****"


def generate_attendance_import_template(class_section: ClassSection = None, subject: Subject = None) -> io.BytesIO:
    """Generates a downloadable Excel template with pre-filled enrolled students if class is specified."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Entry"

    # Header styling
    header_fill = PatternFill(start_color="24483D", end_color="24483D", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    thin_border = Border(
        left=Side(style='thin', color='E4E0D6'),
        right=Side(style='thin', color='E4E0D6'),
        top=Side(style='thin', color='E4E0D6'),
        bottom=Side(style='thin', color='E4E0D6')
    )

    headers = ["Roll Number", "Student Name", "Subject Code", "Date (YYYY-MM-DD)", "Period (1-8)", "Status (PRESENT/ABSENT/EXCUSED)", "Remarks"]
    ws.append(headers)

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border

    today_str = timezone.now().date().strftime("%Y-%m-%d")
    subj_code = subject.code if subject else "AI701"

    # Prefill sample or class students
    if class_section:
        students = class_section.students.all().select_related('user').order_by('roll_number')
        for s in students:
            ws.append([
                s.roll_number,
                s.user.get_full_name() or s.roll_number,
                subj_code,
                today_str,
                1,
                "PRESENT",
                ""
            ])
    else:
        # Sample rows
        ws.append(["23AI001", "Aarav Sharma", "AI701", today_str, 1, "PRESENT", ""])
        ws.append(["23AI002", "Bhavya Patel", "AI701", today_str, 1, "ABSENT", "Uninformed absence"])
        ws.append(["23AI003", "Chirag Reddy", "AI701", today_str, 1, "EXCUSED", "Smart India Hackathon"])

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def parse_and_validate_attendance_excel(file_obj) -> Dict[str, Any]:
    """
    Parses uploaded Excel workbook, checks columns, validates references,
    detects duplicates, and returns structured preview with row-level diagnostics.
    """
    try:
        wb = openpyxl.load_workbook(file_obj, data_only=True)
        ws = wb.active
    except Exception as exc:
        return {'success': False, 'error': f"Invalid Excel file: {str(exc)}", 'rows': [], 'errors': []}

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {'success': False, 'error': "The uploaded workbook is empty.", 'rows': [], 'errors': []}

    header_row = [str(cell).strip() if cell is not None else "" for cell in rows[0]]
    expected_cols = ["roll number", "subject code", "date", "period", "status"]

    header_map = {}
    for idx, col in enumerate(header_row):
        col_lower = col.lower()
        for exp in expected_cols:
            if exp in col_lower:
                header_map[exp] = idx

    missing_cols = [c for c in expected_cols if c not in header_map]
    if missing_cols:
        return {
            'success': False,
            'error': f"Missing required column headers: {', '.join(missing_cols)}. Please use the standard template.",
            'rows': [],
            'errors': []
        }

    # Pre-fetch lookup caches for high performance
    all_students = {s.roll_number.upper(): s for s in StudentProfile.objects.all().select_related('user', 'class_section')}
    all_subjects = {s.code.upper(): s for s in Subject.objects.all()}

    valid_rows = []
    error_rows = []
    seen_in_file = set()

    for row_num, row_data in enumerate(rows[1:], start=2):
        # Skip completely empty rows
        if not any(row_data):
            continue

        roll_val = row_data[header_map['roll number']]
        subj_val = row_data[header_map['subject code']]
        date_val = row_data[header_map['date']]
        period_val = row_data[header_map['period']]
        status_val = row_data[header_map['status']]
        remarks_val = row_data[header_map.get('remarks', len(row_data) - 1)] if 'remarks' in header_map else ""

        roll = str(roll_val).strip().upper() if roll_val else ""
        subj_code = str(subj_val).strip().upper() if subj_val else ""
        status_str = str(status_val).strip().upper() if status_val else ""

        row_errors = []

        # 1. Roll number validation
        student = all_students.get(roll)
        if not roll:
            row_errors.append("Roll Number is empty.")
        elif not student:
            row_errors.append(f"Student roll '{roll}' not found in registered records.")

        # 2. Subject validation
        subject = all_subjects.get(subj_code)
        if not subj_code:
            row_errors.append("Subject Code is empty.")
        elif not subject:
            row_errors.append(f"Subject '{subj_code}' does not exist.")

        # 3. Date validation
        parsed_date = None
        if isinstance(date_val, (datetime, date)):
            parsed_date = date_val.date() if isinstance(date_val, datetime) else date_val
        elif isinstance(date_val, str):
            try:
                parsed_date = datetime.strptime(date_val.strip(), "%Y-%m-%d").date()
            except ValueError:
                try:
                    parsed_date = datetime.strptime(date_val.strip(), "%d-%m-%Y").date()
                except ValueError:
                    row_errors.append(f"Invalid date format '{date_val}'. Expected YYYY-MM-DD.")
        else:
            row_errors.append("Date is missing or has an unsupported format.")

        # 4. Period validation
        try:
            period = int(period_val)
            if not (1 <= period <= 8):
                row_errors.append(f"Period must be between 1 and 8 (got {period}).")
        except (ValueError, TypeError):
            row_errors.append(f"Period '{period_val}' is not a valid integer.")
            period = 1

        # 5. Status validation
        if status_str not in ('PRESENT', 'ABSENT', 'EXCUSED'):
            row_errors.append(f"Invalid status '{status_str}'. Must be PRESENT, ABSENT, or EXCUSED.")

        # 6. Duplicate check within file
        entry_key = (roll, subj_code, str(parsed_date), period)
        if entry_key in seen_in_file:
            row_errors.append("Duplicate row inside this spreadsheet for the same student, subject, date, and period.")
        seen_in_file.add(entry_key)

        item = {
            'row_num': row_num,
            'roll_number': roll,
            'student_name': student.user.get_full_name() if student else "",
            'subject_code': subj_code,
            'date': str(parsed_date) if parsed_date else str(date_val),
            'parsed_date': parsed_date,
            'period': period,
            'status': status_str,
            'remarks': str(remarks_val or '').strip(),
            'student_id': student.id if student else None,
            'subject_id': subject.id if subject else None,
            'class_section_id': student.class_section_id if student else None,
            'errors': row_errors,
        }

        if row_errors:
            error_rows.append(item)
        else:
            valid_rows.append(item)

    return {
        'success': True,
        'total_rows': len(valid_rows) + len(error_rows),
        'valid_count': len(valid_rows),
        'error_count': len(error_rows),
        'valid_rows': valid_rows,
        'error_rows': error_rows,
    }


def commit_attendance_import(valid_rows: List[Dict[str, Any]], user: User) -> Dict[str, Any]:
    """
    Atomically commits validated rows into AttendanceSession and AttendanceRecord tables.
    Recalculates student metrics and triggers parent alerts for absences.
    """
    if not valid_rows:
        return {'success': False, 'message': "No valid rows to commit.", 'committed_records': 0}

    # Group rows by session (class_section_id, subject_id, date, period)
    session_map = {}
    for r in valid_rows:
        session_key = (r['class_section_id'], r['subject_id'], r['parsed_date'], r['period'])
        if session_key not in session_map:
            session_map[session_key] = []
        session_map[session_key].append(r)

    created_records_count = 0
    updated_records_count = 0
    affected_students = set()

    with transaction.atomic():
        for (class_section_id, subject_id, date_obj, period_num), rows_in_session in session_map.items():
            if not class_section_id or not subject_id:
                continue

            session, _ = AttendanceSession.objects.get_or_create(
                class_section_id=class_section_id,
                subject_id=subject_id,
                date=date_obj,
                period_number=period_num,
                defaults={
                    'status': SessionStatus.SUBMITTED,
                    'submitted_by': user,
                    'topic_covered': f"Batch import via spreadsheet by {user.username}"
                }
            )

            for item in rows_in_session:
                student_id = item['student_id']
                status = item['status']
                remarks = sanitize_cell_value(item['remarks'])

                record, created = AttendanceRecord.objects.update_or_create(
                    session=session,
                    student_id=student_id,
                    defaults={
                        'status': status,
                        'remarks': remarks,
                        'recorded_by': user
                    }
                )

                if created:
                    created_records_count += 1
                else:
                    updated_records_count += 1

                affected_students.add(student_id)

                # Send parent absence alerts if marked absent
                if status == 'ABSENT':
                    notify_parents_of_absence(record)

        # Audit log entry
        AuditLog.objects.create(
            user=user,
            action="EXCEL_ATTENDANCE_IMPORT",
            model_name="AttendanceRecord",
            object_id=f"count={created_records_count + updated_records_count}",
            details=f"Committed {created_records_count} new and {updated_records_count} updated records for {len(affected_students)} students."
        )

    # Recalculate student metrics for all affected students
    for st_id in affected_students:
        try:
            st = StudentProfile.objects.get(id=st_id)
            recalculate_and_sync_student_metrics(st)
        except Exception:
            pass

    return {
        'success': True,
        'message': f"Successfully processed {created_records_count + updated_records_count} records ({created_records_count} created, {updated_records_count} updated).",
        'committed_records': created_records_count + updated_records_count,
        'affected_students_count': len(affected_students)
    }


def export_at_risk_students_excel(students_queryset) -> io.BytesIO:
    """Exports list of At-Risk and Low Attendance students with metrics and parent contacts."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "At-Risk Students"

    header_fill = PatternFill(start_color="B54743", end_color="B54743", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")

    headers = [
        "Roll Number", "Student Name", "Class Section", "Department",
        "Attendance %", "Risk Status", "Phone", "Parent Name", "Parent Contact", "Emergency Contact"
    ]
    ws.append(headers)

    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for st in students_queryset:
        parent_rel = st.parent_relations.first()
        parent_name = parent_rel.parent.user.get_full_name() if parent_rel else "N/A"
        parent_phone = parent_rel.parent.user.profile.phone if parent_rel and hasattr(parent_rel.parent.user, 'profile') else "N/A"

        ws.append([
            sanitize_cell_value(st.roll_number),
            sanitize_cell_value(st.user.get_full_name() or st.user.username),
            sanitize_cell_value(st.class_section.name if st.class_section else "N/A"),
            sanitize_cell_value(st.class_section.department.code if st.class_section else "N/A"),
            st.cached_attendance_percentage,
            st.cached_risk_level,
            sanitize_cell_value(mask_phone_value(getattr(st.user, 'profile', None).phone if hasattr(st.user, 'profile') else "")),
            sanitize_cell_value(parent_name),
            sanitize_cell_value(mask_phone_value(parent_phone)),
            sanitize_cell_value(mask_phone_value(st.emergency_contact))
        ])

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def export_subject_attendance_excel(class_section: ClassSection, subject: Subject) -> io.BytesIO:
    """Exports comprehensive period-by-period class attendance sheet."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{subject.code} Attendance"

    header_fill = PatternFill(start_color="24483D", end_color="24483D", fill_type="solid")
    header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")

    # Fetch all sessions for this class and subject
    sessions = AttendanceSession.objects.filter(
        class_section=class_section,
        subject=subject,
        is_cancelled=False
    ).order_by('date', 'period_number')

    session_list = list(sessions)
    students = class_section.students.all().select_related('user').order_by('roll_number')

    # Headers: Roll, Name, [Date P#...], Total Attended, Total Sessions, %
    headers = ["Roll Number", "Student Name"]
    for s in session_list:
        headers.append(f"{s.date.strftime('%m/%d')} P{s.period_number}")
    headers.extend(["Attended", "Total Eligible", "Attendance %"])

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Records lookup map
    records = AttendanceRecord.objects.filter(
        session__in=session_list
    ).values('student_id', 'session_id', 'status')

    rec_map = {(r['student_id'], r['session_id']): r['status'] for r in records}

    for st in students:
        row = [
            sanitize_cell_value(st.roll_number),
            sanitize_cell_value(st.user.get_full_name() or st.user.username)
        ]
        attended = 0
        for s in session_list:
            stat = rec_map.get((st.id, s.id), "-")
            if stat in ('PRESENT', 'EXCUSED'):
                attended += 1
                row.append("P" if stat == 'PRESENT' else "OD")
            elif stat == 'ABSENT':
                row.append("A")
            else:
                row.append("-")

        total = len(session_list)
        pct = round((attended / total * 100), 1) if total > 0 else 100.0
        row.extend([attended, total, pct])
        ws.append(row)

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
