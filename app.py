from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from decimal import Decimal, InvalidOperation
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "banking_system_secret_key_change_in_production"

# ----------------------------------------------------------------
# DATABASE CONNECTION
# ----------------------------------------------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="banking_system"
    )

# ----------------------------------------------------------------
# HELPER: safe Decimal conversion
# ----------------------------------------------------------------
def parse_decimal(value):
    """Return a Decimal from a stripped string, or None on failure."""
    try:
        value = str(value).strip()
        if value == "":
            return None
        d = Decimal(value)
        if d <= 0:
            return None
        return d
    except (InvalidOperation, ValueError):
        return None

# ----------------------------------------------------------------
# HELPER: get all accounts for the logged-in user
# ----------------------------------------------------------------
def get_user_accounts(user_id):
    """Return a list of account dicts for the given user."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT account_id, account_type, balance FROM accounts WHERE user_id = %s ORDER BY account_id",
            (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        db.close()

# ----------------------------------------------------------------
# AUTH DECORATOR
# ----------------------------------------------------------------
def login_required(f):
    """Redirect to login page if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ================================================================
#  REGISTER
# ================================================================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    gmail = email # Map single input to both schema columns
    aadhar_number = request.form.get("aadhar_number", "").strip()
    phone = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()
    confirm = request.form.get("confirm_password", "").strip()

    if not username or not email or not password or not aadhar_number or not phone:
        flash("All fields are required.", "error")
        return render_template("register.html")

    if password != confirm:
        flash("Passwords do not match.", "error")
        return render_template("register.html")

    if len(password) < 4:
        flash("Password must be at least 4 characters.", "error")
        return render_template("register.html")

    if len(aadhar_number) != 12 or not aadhar_number.isdigit():
        flash("Aadhar number must be exactly 12 digits.", "error")
        return render_template("register.html")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM users WHERE username = %s OR email = %s OR gmail = %s OR aadhar_number = %s",
                       (username, email, gmail, aadhar_number))
        if cursor.fetchone():
            flash("Username, email, gmail, or aadhar already taken.", "error")
            return render_template("register.html")

        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, email, gmail, aadhar_number, phone, password_hash)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (username, email, gmail, aadhar_number, phone, hashed))

        user_id = cursor.lastrowid

        # Auto-create a default account for the new user
        cursor.execute("""
            INSERT INTO accounts (user_id, balance) VALUES (%s, 0.00)
        """, (user_id,))

        db.commit()
        flash("Registration successful! A default account has been created. Please log in.", "success")
        return redirect(url_for("login"))
    finally:
        cursor.close()
        db.close()

# ================================================================
#  LOGIN
# ================================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Please enter username and password.", "error")
        return render_template("login.html")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        flash("Welcome back, " + user["username"] + "!", "success")
        return redirect(url_for("home"))
    finally:
        cursor.close()
        db.close()

# ================================================================
#  LOGOUT
# ================================================================
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# ================================================================
#  CREATE ACCOUNT (new — allows multiple accounts per user)
# ================================================================
# DBMS Concept: This demonstrates the 1:N (one-to-many) relationship
# between users and accounts. One user can own many accounts, but
# each account belongs to exactly one user (enforced by the FK).
# ================================================================
@app.route("/create_account", methods=["GET", "POST"])
@login_required
def create_account():
    user_id = session["user_id"]

    if request.method == "GET":
        accounts = get_user_accounts(user_id)
        return render_template("create_account.html", accounts=accounts)

    # --- POST ---
    initial_deposit = parse_decimal(request.form.get("initial_deposit", "0"))
    account_type = request.form.get("account_type", "Savings").strip()
    if account_type not in ("Savings", "Current"):
        account_type = "Savings"

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Always create with 0 balance — trigger handles deposits
        cursor.execute("""
            INSERT INTO accounts (user_id, account_type, balance) VALUES (%s, %s, 0.00)
        """, (user_id, account_type))

        new_account_id = cursor.lastrowid

        # If initial deposit > 0, insert transaction (trigger adds to balance)
        if initial_deposit and initial_deposit > 0:
            cursor.execute("""
                INSERT INTO transactions (account_id, type, amount, status)
                VALUES (%s, 'DEPOSIT', %s, 'SUCCESS')
            """, (new_account_id, str(initial_deposit)))

        db.commit()
        flash("New account #" + str(new_account_id) + " created!", "success")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("home"))

# ================================================================
#  HOME / DASHBOARD (with summary cards)
# ================================================================
@app.route("/")
@login_required
def home():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Get user info and mask Aadhar
        cursor.execute("SELECT username as name, email, gmail, aadhar_number, phone FROM users WHERE user_id = %s", (user_id,))
        user_info = cursor.fetchone()
        if user_info and user_info.get("aadhar_number"):
            aadhar = user_info["aadhar_number"]
            user_info["aadhar_masked"] = f"XXXX-XXXX-{aadhar[-4:]}" if len(aadhar) == 12 else "XXXX-XXXX-XXXX"
            # Remove raw aadhar from dictionary to prevent accidental exposure
            del user_info["aadhar_number"]
        else:
            if user_info:
                user_info["aadhar_masked"] = "N/A"
            else:
                user_info = {}

        # Get user's accounts
        cursor.execute("SELECT * FROM accounts WHERE user_id = %s ORDER BY account_id", (user_id,))
        accounts = cursor.fetchall()

        # Total balance across all accounts
        cursor.execute("""
            SELECT COALESCE(SUM(balance), 0) AS total_balance
            FROM accounts WHERE user_id = %s
        """, (user_id,))
        total_balance = cursor.fetchone()["total_balance"]

        # Total deposits & withdrawals
        cursor.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN t.type='DEPOSIT'  AND t.status='SUCCESS' THEN t.amount ELSE 0 END), 0) AS total_deposits,
                COALESCE(SUM(CASE WHEN t.type='WITHDRAW' AND t.status='SUCCESS' THEN t.amount ELSE 0 END), 0) AS total_withdrawals,
                COUNT(*) AS txn_count
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.user_id = %s
        """, (user_id,))
        txn_stats = cursor.fetchone()

        # Active loans
        cursor.execute("""
            SELECT COUNT(*) AS active_loans,
                   COALESCE(SUM(remaining_amount), 0) AS total_remaining
            FROM loans WHERE user_id = %s AND status = 'ACTIVE'
        """, (user_id,))
        loan_stats = cursor.fetchone()

        # Recent transactions (top 5) for dashboard sidebar
        cursor.execute("""
            SELECT t.transaction_id, t.type, t.amount, t.created_at, t.status, a.account_id
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.user_id = %s
            ORDER BY t.created_at DESC
            LIMIT 5
        """, (user_id,))
        recent_txns = cursor.fetchall()

        return render_template("index.html",
                               user_info=user_info,
                               accounts=accounts,
                               total_balance=total_balance,
                               txn_stats=txn_stats,
                               loan_stats=loan_stats,
                               recent_txns=recent_txns)
    finally:
        cursor.close()
        db.close()

# ================================================================
#  DEPOSIT (with account dropdown)
# ================================================================
@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    user_id = session["user_id"]
    accounts = get_user_accounts(user_id)

    if request.method == "GET":
        return render_template("deposit.html", accounts=accounts)

    # --- POST ---
    account_id = request.form.get("account_id", "").strip()
    amount = parse_decimal(request.form.get("amount", ""))

    if not account_id or amount is None:
        flash("Please select an account and enter a positive amount.", "error")
        return render_template("deposit.html", accounts=accounts)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Verify account belongs to logged-in user
        cursor.execute("SELECT account_id FROM accounts WHERE account_id = %s AND user_id = %s",
                       (account_id, user_id))
        if cursor.fetchone() is None:
            flash("Account not found or does not belong to you.", "error")
            return render_template("deposit.html", accounts=accounts)

        # Insert transaction — trigger auto-updates balance
        cursor.execute("""
            INSERT INTO transactions (account_id, type, amount, status)
            VALUES (%s, 'DEPOSIT', %s, 'SUCCESS')
        """, (account_id, str(amount)))
        db.commit()
        flash("Deposit of ₹" + str(amount) + " to Account #" + str(account_id) + " successful!", "success")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("deposit"))

# ================================================================
#  WITHDRAW (with account dropdown)
# ================================================================
@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    user_id = session["user_id"]
    accounts = get_user_accounts(user_id)

    if request.method == "GET":
        return render_template("withdraw.html", accounts=accounts)

    # --- POST ---
    account_id = request.form.get("account_id", "").strip()
    amount = parse_decimal(request.form.get("amount", ""))

    if not account_id or amount is None:
        flash("Please select an account and enter a positive amount.", "error")
        return render_template("withdraw.html", accounts=accounts)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT account_id FROM accounts WHERE account_id = %s AND user_id = %s",
                       (account_id, user_id))
        if cursor.fetchone() is None:
            flash("Account not found or does not belong to you.", "error")
            return render_template("withdraw.html", accounts=accounts)

        # Insert as SUCCESS — trigger downgrades to FAILED if insufficient
        cursor.execute("""
            INSERT INTO transactions (account_id, type, amount, status)
            VALUES (%s, 'WITHDRAW', %s, 'SUCCESS')
        """, (account_id, str(amount)))
        db.commit()
        flash("Withdrawal from Account #" + str(account_id) + " processed.", "success")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("withdraw"))

# ================================================================
#  TRANSFER (with account dropdown for sender)
# ================================================================
@app.route("/transfer", methods=["GET", "POST"])
@login_required
def transfer():
    user_id = session["user_id"]
    accounts = get_user_accounts(user_id)

    if request.method == "GET":
        return render_template("transfer.html", accounts=accounts)

    # --- POST ---
    from_acc = request.form.get("from_account", "").strip()
    to_acc = request.form.get("to_account", "").strip()
    amount = parse_decimal(request.form.get("amount", ""))

    if not from_acc or not to_acc or amount is None:
        flash("Please fill in all fields with valid values.", "error")
        return render_template("transfer.html", accounts=accounts)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Verify sender account belongs to logged-in user
        cursor.execute("SELECT account_id FROM accounts WHERE account_id = %s AND user_id = %s",
                       (from_acc, user_id))
        if cursor.fetchone() is None:
            flash("Sender account not found or does not belong to you.", "error")
            return render_template("transfer.html", accounts=accounts)

        cursor2 = db.cursor()
        cursor2.callproc("sp_transfer_money", (int(from_acc), int(to_acc), str(amount)))
        db.commit()
        cursor2.close()
        flash("Transfer of ₹" + str(amount) + " successful!", "success")
    except mysql.connector.Error as e:
        db.rollback()
        msg = str(e)
        if "Insufficient balance" in msg:
            flash("Insufficient balance for transfer.", "error")
        elif "same account" in msg:
            flash("Cannot transfer to the same account.", "error")
        elif "does not exist" in msg:
            flash("One or both accounts not found.", "error")
        else:
            flash("Transfer failed: " + msg, "error")
        return render_template("transfer.html", accounts=accounts)
    except (ValueError, TypeError):
        flash("Invalid account ID.", "error")
        return render_template("transfer.html", accounts=accounts)
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("transfer"))

# ================================================================
#  TRANSACTIONS (filtered to user's accounts)
# ================================================================
@app.route("/transactions")
@login_required
def transactions():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT t.* FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.user_id = %s
            ORDER BY t.created_at DESC, t.transaction_id DESC
        """, (user_id,))
        data = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("transactions.html", transactions=data)

# ================================================================
#  APPLY LOAN (with account dropdown)
# ================================================================
@app.route("/apply_loan", methods=["GET", "POST"])
@login_required
def apply_loan():
    user_id = session["user_id"]
    accounts = get_user_accounts(user_id)

    if request.method == "GET":
        return render_template("apply_loan.html", accounts=accounts)

    # --- POST ---
    account_id = request.form.get("account_id", "").strip()
    amount = parse_decimal(request.form.get("amount", ""))
    interest_rate = parse_decimal(request.form.get("interest_rate", ""))

    if not account_id or amount is None or interest_rate is None:
        flash("Please fill in all fields with valid positive values.", "error")
        return render_template("apply_loan.html", accounts=accounts)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Verify account belongs to logged-in user
        cursor.execute("SELECT account_id FROM accounts WHERE account_id = %s AND user_id = %s",
                       (account_id, user_id))
        if cursor.fetchone() is None:
            flash("Account not found or does not belong to you.", "error")
            return render_template("apply_loan.html", accounts=accounts)

        # Calculate remaining = loan_amount + interest
        remaining_amount = amount + (amount * interest_rate / Decimal("100"))

        # Insert loan
        cursor.execute("""
            INSERT INTO loans (user_id, account_id, loan_amount, remaining_amount, interest_rate, status)
            VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
        """, (user_id, account_id, str(amount), str(remaining_amount), str(interest_rate)))

        # Credit account balance (loan disbursement)
        cursor.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s",
                       (str(amount), account_id))

        db.commit()
        flash("Loan of ₹" + str(amount) + " approved and credited to Account #" + str(account_id) + "!", "success")
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("loans"))

# ================================================================
#  LOANS HISTORY (filtered to user)
# ================================================================
@app.route("/loans")
@login_required
def loans():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT l.* FROM loans l
            WHERE l.user_id = %s
            ORDER BY l.loan_id DESC
        """, (user_id,))
        data = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("loans.html", loans=data)

# ================================================================
#  PAY LOAN (with loan + account dropdowns)
# ================================================================
@app.route("/pay_loan", methods=["GET", "POST"])
@login_required
def pay_loan():
    user_id = session["user_id"]

    # Helper: fetch active loans for the logged-in user
    def get_user_loans():
        db2 = get_db()
        cur2 = db2.cursor(dictionary=True)
        try:
            cur2.execute("""
                SELECT loan_id, remaining_amount
                FROM loans WHERE user_id = %s AND status = 'ACTIVE'
                ORDER BY loan_id
            """, (user_id,))
            return cur2.fetchall()
        finally:
            cur2.close()
            db2.close()

    accounts = get_user_accounts(user_id)
    loans_list = get_user_loans()

    if request.method == "GET":
        return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

    # --- POST ---
    loan_id = request.form.get("loan_id", "").strip()
    account_id = request.form.get("account_id", "").strip()
    payment_amount = parse_decimal(request.form.get("payment_amount", ""))

    if not loan_id or not account_id or payment_amount is None:
        flash("Please select a loan, an account, and enter a positive payment amount.", "error")
        return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # --- Atomic transaction for financial safety with Row-Level Locking ---
        cursor.execute("START TRANSACTION")

        # Verify loan belongs to user and is active. Lock it to prevent concurrent payments.
        cursor.execute("SELECT * FROM loans WHERE loan_id = %s AND user_id = %s FOR UPDATE",
                       (loan_id, user_id))
        loan = cursor.fetchone()

        if loan is None:
            cursor.execute("ROLLBACK")
            flash("Loan not found or does not belong to you.", "error")
            return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

        if loan["status"] == "PAID":
            cursor.execute("ROLLBACK")
            flash("This loan is already fully paid.", "error")
            return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

        remaining = Decimal(str(loan["remaining_amount"]))

        if payment_amount > remaining:
            cursor.execute("ROLLBACK")
            flash("Payment amount exceeds remaining loan balance.", "error")
            return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

        # Verify account belongs to user and has sufficient balance. Lock it to prevent dirty reads/lost updates.
        cursor.execute("SELECT balance FROM accounts WHERE account_id = %s AND user_id = %s FOR UPDATE",
                       (account_id, user_id))
        acc = cursor.fetchone()

        if acc is None:
            cursor.execute("ROLLBACK")
            flash("Account not found or does not belong to you.", "error")
            return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

        balance = Decimal(str(acc["balance"]))

        if payment_amount > balance:
            cursor.execute("ROLLBACK")
            flash("Insufficient balance in Account #" + str(account_id) + " for this payment.", "error")
            return render_template("pay_loan.html", loans=loans_list, accounts=accounts)

        # Deduct from selected account
        cursor.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s",
                       (str(payment_amount), account_id))

        # Calculate new remaining balance
        new_remaining = remaining - payment_amount

        # Record payment FIRST (trigger checks remaining_amount before it's reduced)
        cursor.execute("""
            INSERT INTO loan_payments (loan_id, account_id, amount_paid, remaining_balance)
            VALUES (%s, %s, %s, %s)
        """, (loan_id, account_id, str(payment_amount), str(new_remaining)))

        # THEN update loan remaining balance
        cursor.execute("UPDATE loans SET remaining_amount = %s WHERE loan_id = %s",
                       (str(new_remaining), loan_id))

        db.commit()
        flash("Payment of ₹" + str(payment_amount) + " from Account #" + str(account_id) + " recorded!", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash("Payment failed: " + str(e), "error")
        return render_template("pay_loan.html", loans=loans_list, accounts=accounts)
    finally:
        cursor.close()
        db.close()

    return redirect(url_for("loans"))

# ================================================================
#  LOAN PAYMENTS HISTORY (filtered to user's loans)
# ================================================================
@app.route("/loan_payments")
@login_required
def loan_payments():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT lp.* FROM loan_payments lp
            JOIN loans l ON lp.loan_id = l.loan_id
            WHERE l.user_id = %s
            ORDER BY lp.payment_date DESC, lp.payment_id DESC
        """, (user_id,))
        data = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("loan_payments.html", payments=data)

# ================================================================
#  REPORTS: Monthly Transaction Summary
# ================================================================
@app.route("/reports/monthly")
@login_required
def report_monthly():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                YEAR(t.created_at) AS txn_year,
                MONTH(t.created_at) AS txn_month,
                COUNT(*) AS total_transactions,
                SUM(CASE WHEN t.type='DEPOSIT'  AND t.status='SUCCESS' THEN t.amount ELSE 0 END) AS total_deposits,
                SUM(CASE WHEN t.type='WITHDRAW' AND t.status='SUCCESS' THEN t.amount ELSE 0 END) AS total_withdrawals,
                SUM(CASE WHEN t.status='FAILED' THEN 1 ELSE 0 END) AS failed_count
            FROM transactions t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE a.user_id = %s
            GROUP BY YEAR(t.created_at), MONTH(t.created_at)
            ORDER BY txn_year DESC, txn_month DESC
        """, (user_id,))
        data = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("reports_monthly.html", reports=data)

# ================================================================
#  REPORTS: Loan Analytics
# ================================================================
@app.route("/reports/loans")
@login_required
def report_loans():
    user_id = session["user_id"]
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT loan_id, account_id, loan_amount, remaining_amount, interest_rate,
                   (loan_amount * interest_rate / 100) AS interest_earned,
                   status
            FROM loans
            WHERE user_id = %s
            ORDER BY loan_id DESC
        """, (user_id,))
        loan_details = cursor.fetchall()

        cursor.execute("""
            SELECT
                COUNT(*) AS total_loans,
                SUM(CASE WHEN status='ACTIVE' THEN 1 ELSE 0 END) AS active_count,
                SUM(CASE WHEN status='PAID'   THEN 1 ELSE 0 END) AS paid_count,
                COALESCE(SUM(loan_amount), 0) AS total_borrowed,
                COALESCE(SUM(loan_amount * interest_rate / 100), 0) AS total_interest,
                COALESCE(SUM(remaining_amount), 0) AS total_remaining
            FROM loans
            WHERE user_id = %s
        """, (user_id,))
        summary = cursor.fetchone()
    finally:
        cursor.close()
        db.close()
    return render_template("reports_loans.html", loans=loan_details, summary=summary)

# ================================================================
# ================================================================
#  ADMIN: Audit Accounts (Table-Level Locking)
# ================================================================
@app.route("/admin/audit")
@login_required
def admin_audit():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Implement table-level locking for bulk operations
        cursor.execute("LOCK TABLES accounts WRITE")
        
        cursor.execute("SELECT COUNT(*) AS total_accounts, COALESCE(SUM(balance), 0) AS total_system_balance FROM accounts")
        audit_data = cursor.fetchone()
        
    finally:
        # Always unlock in a finally block to prevent database deadlocks
        try:
            cursor.execute("UNLOCK TABLES")
        except:
            pass
        cursor.close()
        db.close()
        
    flash(f"System Audit Complete! Total Accounts: {audit_data['total_accounts']}, Total Bank Balance: ₹{audit_data['total_system_balance']}", "success")
    return redirect(url_for("home"))

# ================================================================
#  DATABASE FEATURES PAGE
# ================================================================
@app.route("/database_features")
@login_required
def database_features():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        # Tables
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS, CREATE_TIME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'banking_system' AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()

        # Triggers
        cursor.execute("""
            SELECT TRIGGER_NAME, EVENT_MANIPULATION, EVENT_OBJECT_TABLE, ACTION_TIMING
            FROM INFORMATION_SCHEMA.TRIGGERS
            WHERE TRIGGER_SCHEMA = 'banking_system'
            ORDER BY TRIGGER_NAME
        """)
        triggers = cursor.fetchall()

        # Stored Procedures
        cursor.execute("""
            SELECT ROUTINE_NAME, ROUTINE_TYPE, CREATED
            FROM INFORMATION_SCHEMA.ROUTINES
            WHERE ROUTINE_SCHEMA = 'banking_system'
            ORDER BY ROUTINE_NAME
        """)
        procedures = cursor.fetchall()

        # Indexes
        cursor.execute("""
            SELECT DISTINCT INDEX_NAME, TABLE_NAME, COLUMN_NAME, NON_UNIQUE
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = 'banking_system'
            ORDER BY TABLE_NAME, INDEX_NAME
        """)
        indexes = cursor.fetchall()

        # Views
        cursor.execute("""
            SELECT TABLE_NAME AS VIEW_NAME
            FROM INFORMATION_SCHEMA.VIEWS
            WHERE TABLE_SCHEMA = 'banking_system'
            ORDER BY TABLE_NAME
        """)
        views = cursor.fetchall()

    finally:
        cursor.close()
        db.close()

    return render_template("database_features.html",
                           tables=tables,
                           triggers=triggers,
                           procedures=procedures,
                           indexes=indexes,
                           views=views)

# ----------------------------------------------------------------
if __name__ == "__main__":
    from waitress import serve
    print("Starting production WSGI server on http://0.0.0.0:5000")
    serve(app, host="0.0.0.0", port=5000)