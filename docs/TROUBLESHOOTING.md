# Troubleshooting & Frequently Asked Questions

This document covers solutions for common setup, migration, and runtime issues.

---

## 1. Port 8000 Already in Use

**Symptom:**
`Error: That port is already in use.`

**Fix:**
Run the development server on an alternative port (e.g. 8001):
```cmd
.\.venv\Scripts\python manage.py runserver 127.0.0.1:8001
```

Or terminate the process holding port 8000 on Windows:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

---

## 2. Missing Virtual Environment Error in `run.bat`

**Symptom:**
`[ERROR] Virtual environment .venv was not found.`

**Fix:**
Execute `setup.bat` once to configure the virtual environment and install all packages:
```cmd
setup.bat
```

---

## 3. Database Out of Sync or Fresh Start Required

If you wish to re-initialize your local database with fresh demonstration data:
```cmd
del db.sqlite3
.\.venv\Scripts\python manage.py migrate
.\.venv\Scripts\python manage.py seed_demo_data
.\.venv\Scripts\python manage.py train_risk_model
```

---

## 4. Excel Import Rejects All Rows

**Causes & Fixes:**
1. **Wrong Column Names:** Ensure the first row has exact or similar headers: `Roll Number`, `Subject Code`, `Date`, `Period`, `Status`. Use `Download Blank Attendance Template` directly from the portal.
2. **Date Format:** Dates must follow standard ISO format `YYYY-MM-DD` (e.g. `2026-10-21`).
3. **Roll Number Unrecognized:** Verify that the student roll numbers in the spreadsheet are registered in the student directory before uploading.

---

## 5. Email Notifications Not Sending to Real Inboxes

**Explanation:**
By default, the platform runs in **Simulated Delivery Mode** using `django.core.mail.backends.console.EmailBackend`. Notifications are rendered in the terminal and stored in the database.

To connect live SMTP (e.g., Google Workspace or SendGrid):
1. Open `.env`.
2. Configure credentials:
   ```env
   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your_institution_email@gmail.com
   EMAIL_HOST_PASSWORD=your_app_password
   ```
