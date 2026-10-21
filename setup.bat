@echo off
setlocal enabledelayedexpansion

echo =====================================================================
echo  Student Attendance Intelligence ^& Early Warning System - Windows Setup
echo =====================================================================
echo.

:: 1. Check Python installation
where py >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3.12"
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python"
    ) else (
        echo [ERROR] Python was not found on your system PATH.
        echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/
        pause
        exit /b 1
    )
)

echo [1/6] Using Python runtime: %PYTHON_CMD%
%PYTHON_CMD% --version

:: 2. Create virtual environment
if not exist ".venv" (
    echo [2/6] Creating isolated virtual environment in .venv ...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2/6] Virtual environment .venv already exists.
)

:: 3. Install dependencies
echo [3/6] Upgrading pip and installing required packages from requirements.txt ...
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Package installation failed. Check network or compiler dependencies.
    pause
    exit /b 1
)

:: 4. Environment file setup
if not exist ".env" (
    echo [4/6] Creating default local .env configuration from .env.example ...
    copy .env.example .env >nul
) else (
    echo [4/6] Existing .env file preserved.
)

:: 5. Run database migrations
echo [5/6] Applying database migrations to local SQLite database ...
.\.venv\Scripts\python manage.py migrate
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Migration failed.
    pause
    exit /b 1
)

:: 6. Seed demonstration data & train ML risk model
echo [6/6] Seeding comprehensive demonstration dataset and training ML classifier ...
.\.venv\Scripts\python manage.py seed_demo_data
.\.venv\Scripts\python manage.py train_risk_model

echo.
echo =====================================================================
echo  SETUP COMPLETE! The system is ready to run.
echo =====================================================================
echo  To start the web application:
echo    double-click run.bat  OR  execute: run.bat
echo.
echo  Demo Credentials:
echo    Administrator : admin        / admin123
echo    Faculty       : prof_ananya  / faculty123
echo    Student (Safe): 23ai001      / student123
echo    Student (Crit): 23ai014      / student123
echo    Parent        : parent_sharma/ parent123
echo =====================================================================
pause
