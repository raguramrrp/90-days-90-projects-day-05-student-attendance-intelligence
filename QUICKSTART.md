# Quickstart Guide

Get the **Student Attendance Intelligence & Early Warning System** running on Windows in under two minutes.

---

## Prerequisites

- **OS:** Windows 10 or 11 (64-bit)
- **Python:** Python 3.10, 3.11, or 3.12 (Check via `py --version` or `python --version`)
- **Git:** Git for Windows (Check via `git --version`)

---

## 1. Automated Setup (Recommended for Windows)

Simply double-click `setup.bat` or run:

```cmd
setup.bat
```

This automated script will:
1. Detect your installed Python runtime.
2. Create an isolated virtual environment in `.venv`.
3. Install all required dependencies from `requirements.txt`.
4. Copy `.env.example` to `.env`.
5. Run database migrations on SQLite.
6. Seed the demonstration dataset (`manage.py seed_demo_data`).
7. Train and evaluate the Decision Tree ML classifier (`manage.py train_risk_model`).

---

## 2. Launch the Application

Double-click `run.bat` or run:

```cmd
run.bat
```

Open your browser and navigate to:

👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 3. Demo Account Credentials

Use the one-click demo login buttons on the login page or manually enter:

| Role | Username | Password |
| :--- | :--- | :--- |
| **Institutional Admin** | `admin` | `admin123` |
| **Faculty Member** | `prof_ananya` | `faculty123` |
| **Student (Safe 92%)** | `23ai001` | `student123` |
| **Student (Critical 68%)** | `23ai014` | `student123` |
| **Parent** | `parent_sharma` | `parent123` |

---

## 4. Run Automated Tests

To verify all 25 unit and integration tests:

```cmd
test.bat
```

Expected output:
```text
Ran 25 tests in ~36s
OK
ALL TESTS PASSED SUCCESSFULLY!
```

---

## 5. Manual Setup (Alternative)

If you prefer executing steps manually without `setup.bat`:

```powershell
# 1. Create and activate virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env

# 4. Migrate database
python manage.py migrate

# 5. Seed demonstration data
python manage.py seed_demo_data
python manage.py train_risk_model

# 6. Start development server
python manage.py runserver 127.0.0.1:8000
```
