"""
Automated Tests for Risk Engine, Early Warning Diagnostics, and ML Prediction Fallback.
"""

from django.test import TestCase
from attendance.models import RiskLevel
from attendance.services.risk_engine import classify_risk_level
from attendance.services.ml_risk_service import is_ml_model_available


class RiskEngineTestCase(TestCase):
    def test_classify_risk_critical(self):
        """Attendance below 75% is classified as CRITICAL."""
        self.assertEqual(classify_risk_level(74.9, 75.0, 80.0), RiskLevel.CRITICAL)
        self.assertEqual(classify_risk_level(62.0, 75.0, 80.0), RiskLevel.CRITICAL)

    def test_classify_risk_warning(self):
        """Attendance between 75% and 80% is classified as WARNING."""
        self.assertEqual(classify_risk_level(75.0, 75.0, 80.0), RiskLevel.WARNING)
        self.assertEqual(classify_risk_level(79.5, 75.0, 80.0), RiskLevel.WARNING)

    def test_classify_risk_safe(self):
        """Attendance at or above 80% is classified as SAFE."""
        self.assertEqual(classify_risk_level(80.0, 75.0, 80.0), RiskLevel.SAFE)
        self.assertEqual(classify_risk_level(95.0, 75.0, 80.0), RiskLevel.SAFE)

    def test_ml_model_status_and_presence(self):
        """Checks whether Decision Tree model artifact is saved and accessible."""
        self.assertTrue(is_ml_model_available(), "ML Decision Tree artifact should exist after training.")
