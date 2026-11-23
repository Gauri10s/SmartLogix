# SmartLogix — Smart Logistics and Delivery Management

A Flask + MySQL logistics management web application built with HTML, CSS, JavaScript and Jinja2.

## Features in Sprint 5 — Administration, Analytics & Release
- Everything from Sprint 4
- Admin dashboard: totals, potential-delay count, recent orders, low-stock attention list
- Team & roles page to promote users to warehouse / delivery / admin
- Analytics: orders-by-status chart and 7-day revenue trend
- Full test suite (17 tests) and final documentation = release candidate

## 1. Requirements
- Python 3.10+
- MySQL Server
- VS Code (recommended)

## 2. Create and activate a virtual environment (Windows PowerShell)
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

## 3. Install dependencies
```powershell
pip install -r requirements.txt
```

## 4. Set up MySQL
Open MySQL Workbench or the MySQL command line and run `database/schema.sql`.

Copy `.env.example` to `.env` and enter your MySQL password:
```env
SECRET_KEY=use-a-long-random-secret
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=smartlogix
```

## 5. Run the application
```powershell
python app.py
```
Open http://127.0.0.1:5000

## 6. Create the first admin
1. Register a normal account using the website.
2. In MySQL, run:
```sql
USE smartlogix;
UPDATE users SET role='admin' WHERE email='your-email@example.com';
```
3. Sign out and sign in again. Your admin dashboard will now be available.

## 7. Add team accounts
Register accounts for your team members. From the admin account, open **Team & roles** and change their roles to Warehouse or Delivery as required.

## 8. Run tests
```powershell
pytest -q
```
The current tests are UI/auth-route smoke tests and do not require a live MySQL connection. Feature/database integration tests should be added as the next testing task.

## Suggested Git workflow
```powershell
git init
git add .
git commit -m "Initial SmartLogix Flask application"
git branch -M main
```

## Notes
- This is a working college-project foundation, not a production deployment.
- Configure `.env` before starting the app.
- The application uses server-side sessions and Werkzeug password hashing.
- Map-based live tracking, email/SMS notifications, payment integration and advanced forecasting are not included in this first version.
