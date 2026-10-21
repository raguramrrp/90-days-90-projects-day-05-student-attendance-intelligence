"""
Automated Tests for Attendance Calculation Engine, Projections, and Edge Cases.
"""

from django.test import TestCase
from attendance.services.calculation_engine import (
    calculate_session_stats, calculate_recovery_projections, simulate_future_attendance
)


class AttendanceCalculationTestCase(TestCase):
    def test_basic_percentage_calculation(self):
        """Validates basic percentage: 18 present out of 20 = 90.0%."""
        stats = calculate_session_stats(present=18, excused=0, total_eligible=20)
        self.assertEqual(stats['percentage'], 90.0)
        self.assertEqual(stats['absent_count'], 2)
        self.assertEqual(stats['effective_attended'], 18)

    def test_excused_counted_as_attended(self):
        """Excused on-duty sessions count towards attended eligible sessions."""
        stats = calculate_session_stats(present=16, excused=2, total_eligible=20)
        self.assertEqual(stats['percentage'], 90.0)
        self.assertEqual(stats['effective_attended'], 18)

    def test_zero_sessions_held_edge_case(self):
        """Zero sessions held does not divide by zero and returns safe default 100%."""
        stats = calculate_session_stats(present=0, excused=0, total_eligible=0)
        self.assertEqual(stats['percentage'], 100.0)
        self.assertFalse(stats['has_sessions'])

    def test_recovery_projection_needed_sessions(self):
        """
        Validates exact mathematical formula for required consecutive attended sessions:
        P = 15, N = 25 (60%). Target T = 75% (0.75).
        Formula: ceil((0.75 * 25 - 15) / (1 - 0.75)) = ceil(3.75 / 0.25) = 15 sessions.
        """
        proj = calculate_recovery_projections(
            effective_attended=15,
            total_eligible=25,
            target_percentage=75.0
        )
        self.assertFalse(proj['is_target_met'])
        self.assertEqual(proj['sessions_needed'], 15)
        self.assertEqual(proj['max_absences_permitted'], 0)

    def test_recovery_projection_margin_of_absence(self):
        """
        Validates maximum permissible absences when above target:
        P = 17, N = 20 (85%). Target T = 75% (0.75).
        Formula: floor((17 - 0.75 * 20) / 0.75) = floor(2 / 0.75) = 2 sessions.
        """
        proj = calculate_recovery_projections(
            effective_attended=17,
            total_eligible=20,
            target_percentage=75.0
        )
        self.assertTrue(proj['is_target_met'])
        self.assertEqual(proj['sessions_needed'], 0)
        self.assertEqual(proj['max_absences_permitted'], 2)

    def test_target_100_percent_impossible_after_absence(self):
        """Target of 100% is impossible once any absence has occurred."""
        proj = calculate_recovery_projections(
            effective_attended=19,
            total_eligible=20,
            target_percentage=100.0
        )
        self.assertFalse(proj['is_recovery_possible'])
        self.assertEqual(proj['sessions_needed'], -1)

    def test_simulation_does_not_mutate_initial_state(self):
        """What-if simulator calculates hypothetical future metrics purely in-memory."""
        sim = simulate_future_attendance(
            effective_attended=15,
            total_eligible=25,
            future_attended=10,
            future_absent=0,
            target_percentage=75.0
        )
        # New attended: 25, New total: 35 -> 25/35 = 71.43%
        self.assertEqual(sim['initial_attended'], 15)
        self.assertEqual(sim['initial_total'], 25)
        self.assertEqual(sim['projected_attended'], 25)
        self.assertEqual(sim['projected_total'], 35)
        self.assertEqual(sim['projected_percentage'], 71.43)
        self.assertEqual(sim['projected_risk'], 'CRITICAL')
