"""
Automated Tests for Authentication and Role-Based Authorization.
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from attendance.models import UserProfile, UserRole, StudentProfile, ParentProfile, FacultyProfile, StudentParentRelation


class AuthAndPermissionsTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_user = User.objects.create_user(username="admin_test", password="password123")
        UserProfile.objects.create(user=self.admin_user, role=UserRole.ADMIN)

        # Faculty user
        self.faculty_user = User.objects.create_user(username="faculty_test", password="password123")
        UserProfile.objects.create(user=self.faculty_user, role=UserRole.FACULTY)
        FacultyProfile.objects.create(user=self.faculty_user, employee_id="TEST_FAC_01")

        # Student A user
        self.student_a_user = User.objects.create_user(username="student_a", password="password123")
        UserProfile.objects.create(user=self.student_a_user, role=UserRole.STUDENT)
        self.student_a = StudentProfile.objects.create(user=self.student_a_user, roll_number="TEST_ST_A", registration_number="REG_A")

        # Student B user
        self.student_b_user = User.objects.create_user(username="student_b", password="password123")
        UserProfile.objects.create(user=self.student_b_user, role=UserRole.STUDENT)
        self.student_b = StudentProfile.objects.create(user=self.student_b_user, roll_number="TEST_ST_B", registration_number="REG_B")

        # Parent A user (linked only to Student A)
        self.parent_a_user = User.objects.create_user(username="parent_a", password="password123")
        UserProfile.objects.create(user=self.parent_a_user, role=UserRole.PARENT)
        self.parent_a = ParentProfile.objects.create(user=self.parent_a_user)
        StudentParentRelation.objects.create(student=self.student_a, parent=self.parent_a)

    def test_successful_login(self):
        """Valid credentials log in successfully and redirect to role portal."""
        response = self.client.post(reverse('login'), {'username': 'admin_test', 'password': 'password123'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('admin_dashboard'))

    def test_invalid_login(self):
        """Invalid credentials fail authentication and stay on login page."""
        response = self.client.post(reverse('login'), {'username': 'admin_test', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_unauthenticated_route_redirects_to_login(self):
        """Protected portal pages redirect unauthenticated users to login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_student_cannot_access_admin_portal(self):
        """Student role receives 403 Forbidden on administrator routes."""
        self.client.login(username='student_a', password='password123')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_student_cannot_access_faculty_portal(self):
        """Student role receives 403 Forbidden on faculty routes."""
        self.client.login(username='student_a', password='password123')
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_parent_cannot_view_unlinked_student(self):
        """Parent A cannot access Student B's details (server-side security)."""
        self.client.login(username='parent_a', password='password123')
        # Parent A is linked to Student A, NOT Student B
        response = self.client.get(reverse('parent_child_detail', kwargs={'student_id': self.student_b.id}))
        self.assertEqual(response.status_code, 403)
