# Automated Testing & Verification Report

## 1. Test Suite Summary

The automated test suite verifies all key modules: authentication, permissions, attendance calculation formulas, recovery projections, risk classification, notifications, dispute workflows, and Excel import validation.

- **Framework:** Django Test Runner & Pytest
- **Total Tests Executed:** 25
- **Status:** **PASS (25/25, 100% Passed)**
- **Execution Time:** ~36 seconds
- **Test Command:** `.\test.bat` or `python manage.py test tests`

---

## 2. Test Coverage Matrix

| Test Suite File | Test Scenario | Verified Behaviors | Result |
| :--- | :--- | :--- | :--- |
| `test_auth_and_permissions.py` | `test_successful_login` | Valid credentials redirect to role-specific dashboard | **PASS** |
| `test_auth_and_permissions.py` | `test_invalid_login` | Invalid credentials display error and block entry | **PASS** |
| `test_auth_and_permissions.py` | `test_unauthenticated_route_redirects` | Protected views redirect to login with next param | **PASS** |
| `test_auth_and_permissions.py` | `test_student_cannot_access_admin` | Student role returns 403 Forbidden on admin pages | **PASS** |
| `test_auth_and_permissions.py` | `test_student_cannot_access_faculty` | Student role returns 403 Forbidden on faculty pages | **PASS** |
| `test_auth_and_permissions.py` | `test_parent_cannot_view_unlinked_student` | Parent receives 403 Forbidden accessing unlinked student | **PASS** |
| `test_attendance_calculations.py`| `test_basic_percentage_calculation` | Accurate calculation (18/20 = 90.0%) | **PASS** |
| `test_attendance_calculations.py`| `test_excused_counted_as_attended` | Approved On-Duty sessions count towards attended | **PASS** |
| `test_attendance_calculations.py`| `test_zero_sessions_held_edge_case` | Zero sessions held handles divide-by-zero safely | **PASS** |
| `test_attendance_calculations.py`| `test_recovery_projection_needed_sessions` | Formula ceil((T*N - P)/(1 - T)) yields exact count | **PASS** |
| `test_attendance_calculations.py`| `test_recovery_projection_margin_of_absence`| Formula floor((P - T*N)/T) yields exact safe margin | **PASS** |
| `test_attendance_calculations.py`| `test_target_100_percent_impossible` | Target 100% after absence returns impossible status | **PASS** |
| `test_attendance_calculations.py`| `test_simulation_does_not_mutate` | What-if simulation does not alter real records | **PASS** |
| `test_risk_and_simulator.py` | `test_classify_risk_critical` | < 75% classified as CRITICAL | **PASS** |
| `test_risk_and_simulator.py` | `test_classify_risk_warning` | 75% to 80% classified as WARNING | **PASS** |
| `test_risk_and_simulator.py` | `test_classify_risk_safe` | >= 80% classified as SAFE | **PASS** |
| `test_risk_and_simulator.py` | `test_ml_model_status_and_presence` | Serialized Decision Tree model exists and is loadable | **PASS** |
| `test_notifications.py` | `test_absence_creates_parent_notification` | Absence creates in-app notification & simulated SMS | **PASS** |
| `test_notifications.py` | `test_duplicate_submission_does_not_duplicate`| Idempotency marker prevents duplicate alerts | **PASS** |
| `test_leave_and_corrections.py`| `test_leave_request_workflow` | Student submit -> Faculty review and approve | **PASS** |
| `test_leave_and_corrections.py`| `test_correction_request_approval_updates`| Dispute approval updates record and syncs metrics | **PASS** |
| `test_excel_import_export.py` | `test_formula_injection_defense` | Prepending quote prevents spreadsheet formula execution | **PASS** |
| `test_excel_import_export.py` | `test_template_generation_returns_valid_wb` | Openpyxl template creates styled Excel headers | **PASS** |
| `test_excel_import_export.py` | `test_parse_valid_excel_data` | Valid rows parse correctly for staging | **PASS** |
| `test_excel_import_export.py` | `test_parse_detects_unknown_student` | Unknown roll numbers and periods flagged as errors | **PASS** |

---

## 3. How to Run the Tests

On Windows:
```cmd
test.bat
```

Or using the Python virtual environment directly:
```cmd
.\.venv\Scripts\python manage.py test tests
```
