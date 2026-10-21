@echo off
setlocal

echo =====================================================================
echo  Starting Student Attendance Intelligence ^& Early Warning Server
echo =====================================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv was not found.
    echo Please run setup.bat first to configure your environment.
    pause
    exit /b 1
)

echo Activating environment and launching Django HTTP server on http://127.0.0.1:8000/ ...
echo.
echo =====================================================================
echo  Open your web browser and visit:
echo    http://127.0.0.1:8000/
echo.
echo  Demo Accounts (Also accessible via 1-click fill on login screen):
echo    - Administrator : admin         / admin123
echo    - Faculty       : prof_ananya   / faculty123
echo    - Student (Safe): 23ai001       / student123
echo    - Student (Crit): 23ai014       / student123
echo    - Parent        : parent_sharma / parent123
echo =====================================================================
echo Press CTRL+C to stop the development server.
echo.

.\.venv\Scripts\python manage.py runserver 127.0.0.1:8000
