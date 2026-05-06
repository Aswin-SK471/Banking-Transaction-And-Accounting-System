# Banking Transaction and Accounting System

## Project Overview
This project is a Flask-based web application integrated with a MySQL database that simulates a banking system. It enables users to manage accounts, perform transactions (deposit, withdraw, transfer), apply for loans, and generate reports.

The system ensures data integrity using constraints, triggers, transactions, and concurrency control mechanisms.

---

## Features
- User registration and login (secure password hashing)
- Account creation and balance management
- Deposit, withdrawal, and fund transfer
- Loan application and repayment tracking
- Transaction history and reporting
- Database triggers for validation and automation
- Stored procedures for secure money transfer
- Concurrency control using locks
- Transaction management using COMMIT, ROLLBACK, SAVEPOINT
- Cursor-based stored procedure for total balance calculation

---

## Tech Stack
- Backend: Flask (Python)
- Frontend: HTML, CSS (Jinja2 Templates)
- Database: MySQL
- Libraries:
  - mysql-connector-python
  - werkzeug

---

## Database Concepts Used
- Normalization (1NF, 2NF, 3NF, BCNF, 4NF, 5NF)
- Constraints (CHECK, FOREIGN KEY)
- Joins and Views
- Triggers
- Stored Procedures
- Cursors
- Transactions (ACID Properties)
- Concurrency Control (Row & Table Locking)

---

## How the System Works
- Users register and log in securely
- Each user can create one or more accounts
- Transactions (deposit, withdraw, transfer) update balances using triggers
- Transfers are handled using stored procedures with rollback safety
- Loans are applied and tracked with repayment history
- Reports use aggregate queries for analytics

---

## How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup MySQL Database
Open MySQL and run:

```sql
CREATE DATABASE banking_system;
USE banking_system;
SOURCE database.sql;
```

### 3. Run the Application
```bash
python app.py
```

### 4. Open in Browser
```
http://127.0.0.1:5000
```

---

## Author
Aswin SK