"""
URL configuration for attendance application.
"""

from django.urls import path
from .views import (
    auth_views, admin_views, faculty_views, student_views, parent_views,
    notification_views, api_views
)

urlpatterns = [
    # Auth & Common
    path('', auth_views.login_view, name='home'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('redirect/', auth_views.dashboard_redirect_view, name='dashboard_redirect'),
    path('profile/', auth_views.profile_view, name='user_profile'),

    # Institutional Administrator Portal
    path('admin-portal/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-portal/students/', admin_views.admin_students_view, name='admin_students'),
    path('admin-portal/faculty/', admin_views.admin_faculty_view, name='admin_faculty'),
    path('admin-portal/parents/', admin_views.admin_parents_view, name='admin_parents'),
    path('admin-portal/classes/', admin_views.admin_classes_view, name='admin_classes'),
    path('admin-portal/subjects/', admin_views.admin_subjects_view, name='admin_subjects'),
    path('admin-portal/timetable/', admin_views.admin_timetable_view, name='admin_timetable'),
    path('admin-portal/policies/', admin_views.admin_policies_view, name='admin_policies'),
    path('admin-portal/import-export/', admin_views.admin_import_export_view, name='admin_import_export'),
    path('admin-portal/audit-logs/', admin_views.admin_audit_logs_view, name='admin_audit_logs'),
    path('admin-portal/notification-logs/', admin_views.admin_notification_logs_view, name='admin_notification_logs'),

    # Faculty Portal
    path('faculty-portal/', faculty_views.faculty_dashboard_view, name='faculty_dashboard'),
    path('faculty-portal/mark-attendance/', faculty_views.faculty_mark_attendance_view, name='faculty_mark_attendance'),
    path('faculty-portal/history/', faculty_views.faculty_attendance_history_view, name='faculty_attendance_history'),
    path('faculty-portal/at-risk/', faculty_views.faculty_at_risk_view, name='faculty_at_risk'),
    path('faculty-portal/leaves/', faculty_views.faculty_leave_reviews_view, name='faculty_leave_reviews'),
    path('faculty-portal/corrections/', faculty_views.faculty_correction_reviews_view, name='faculty_correction_reviews'),
    path('faculty-portal/export-class/', faculty_views.faculty_export_class_view, name='faculty_export_class'),

    # Student Portal
    path('student-portal/', student_views.student_dashboard_view, name='student_dashboard'),
    path('student-portal/my-attendance/', student_views.student_my_attendance_view, name='student_my_attendance'),
    path('student-portal/subject/<int:subject_id>/', student_views.student_subject_detail_view, name='student_subject_detail'),
    path('student-portal/simulator/', student_views.student_attendance_simulator_view, name='student_attendance_simulator'),
    path('student-portal/leaves/', student_views.student_leave_requests_view, name='student_leave_requests'),
    path('student-portal/corrections/', student_views.student_correction_requests_view, name='student_correction_requests'),

    # Parent Portal
    path('parent-portal/', parent_views.parent_dashboard_view, name='parent_dashboard'),
    path('parent-portal/child/<int:student_id>/', parent_views.parent_child_detail_view, name='parent_child_detail'),
    path('parent-portal/absences/', parent_views.parent_absence_history_view, name='parent_absence_history'),
    path('parent-portal/submit-explanation/', parent_views.parent_submit_explanation_view, name='parent_submit_explanation'),
    path('parent-portal/preferences/', parent_views.parent_preferences_view, name='parent_preferences'),

    # Notification Center
    path('notifications/', notification_views.notifications_index_view, name='notifications_index'),
    path('notifications/read/<int:notification_id>/', notification_views.notification_mark_read_view, name='notification_mark_read'),
    path('notifications/read-all/', notification_views.notification_mark_all_read_view, name='notification_mark_all_read'),

    # API Endpoints
    path('api/simulate/', api_views.api_simulate_attendance, name='api_simulate_attendance'),
    path('api/ml-risk/<int:student_id>/', api_views.api_ml_risk_prediction, name='api_ml_risk_prediction'),
]
