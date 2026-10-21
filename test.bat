@echo off
setlocal

echo =====================================================================
echo  Running Automated Test Suite
echo =====================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv was not found.
    echo Please run setup.bat first.
    exit /b 1
)

.\.venv\Scripts\python manage.py test tests
set TEST_EXIT_CODE=%ERRORLEVEL%

echo.
if %TEST_EXIT_CODE% EQU 0 (
    echo =====================================================================
    echo  ALL TESTS PASSED SUCCESSFULLY!
    echo =====================================================================
) else (
    echo =====================================================================
    echo  TEST SUITE REPORTED FAILURES (Exit Code: %TEST_EXIT_CODE%)
    echo =====================================================================
)

exit /b %TEST_EXIT_CODE%
