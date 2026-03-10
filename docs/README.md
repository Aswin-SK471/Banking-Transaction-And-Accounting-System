# Banking System — Project Documentation

## 📌 Overview

A complete Banking System Web Application built as a DBMS academic project. The system allows users to register, log in, and manage their bank accounts including deposits, withdrawals, transfers, loans, and loan repayments.

**Technology Stack:**
- **Backend:** Python 3 + Flask
- **Database:** MySQL
- **Frontend:** HTML5 (Jinja2 templates) + CSS
- **Password Hashing:** werkzeug.security

---

## 🏗 Project Structure

```
BankingSystem/
├── app.py                     # Flask backend (all routes + auth)
├── database.sql               # MySQL schema + triggers + views + procedures
├── requirements.txt           # Python dependencies
├── static/
│   └── style.css              # Global stylesheet
├── templates/
│   ├── base.html              # Shared layout (navbar + flash messages)
│   ├── login.html             # Login form
│   ├── register.html          # Registration form
│   ├── index.html             # Dashboard with summary cards
│   ├── deposit.html           # Deposit form
│   ├── withdraw.html          # Withdrawal form
│   ├── transfer.html          # Transfer form
│   ├── transactions.html      # Transaction history table
│   ├── apply_loan.html        # Loan application form
│   ├── loans.html             # Loan history table
│   ├── pay_loan.html          # Loan payment form
│   ├── loan_payments.html     # Loan payment history
│   ├── reports_monthly.html   # Monthly transaction report
│   └── reports_loans.html     # Loan analytics report
└── docs/
    ├── README.md              # This file
    ├── er_diagram.md          # ER diagram (Mermaid)
    ├── normalization.md       # Normalization analysis (1NF → 3NF)
    └── sql_concepts.md        # SQL concepts demonstrated
```

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- MySQL Server 5.7+ or 8.0+
- pip (Python package manager)

### Step 1: Set Up Database
```sql
-- Open MySQL and run:
SOURCE /path/to/BankingSystem/database.sql;
```
This creates the `banking_system` database with all tables, triggers, views, procedures, and sample data.

### Step 2: Configure Database Connection
Edit `app.py` line 15–18 if your MySQL credentials differ:
```python
host="localhost",
user="root",
password="root123",
database="banking_system"
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python app.py
```

### Step 5: Open in Browser
Navigate to: `http://127.0.0.1:5000/`

### Step 6: Register & Login
- Register a new account (an account with ₹0 balance is auto-created)
- Or use sample data (Note: sample users have placeholder password hashes — register new accounts for testing)

---

## ✨ Features

| Feature | Description |
|---|---|
| User Registration | Create account with username, email, password |
| Login / Logout | Session-based authentication |
| Deposit | Add money to account (trigger auto-updates balance) |
| Withdraw | Remove money (trigger auto-fails if insufficient) |
| Transfer | Move money between accounts (stored procedure) |
| Apply Loan | Get a loan credited to account |
| Pay Loan | Repay loans (auto-marks PAID when fully repaid) |
| Transaction History | View all deposits/withdrawals with SUCCESS/FAILED status |
| Loan History | View all loans with ACTIVE/PAID status |
| Payment History | View all loan payment records |
| Monthly Reports | GROUP BY year/month transaction analytics |
| Loan Analytics | Interest earnings, active vs paid breakdown |
| Dashboard Cards | Real-time summary of balances, loans, transactions |

---

## 🔒 Assumptions

1. Each user gets exactly one account upon registration.
2. Interest is calculated as simple interest: `remaining = loan_amount + (loan_amount × rate / 100)`.
3. Loan payments deduct from the borrower's account balance.
4. Failed withdrawals are logged with status='FAILED' (not silently dropped).
5. Transfer is atomic — both sides succeed or neither does.
6. Password hashing uses werkzeug's scrypt algorithm.
7. All money uses DECIMAL(15,2) — never float.
