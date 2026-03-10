"""
Run this script ONCE to initialize the banking_system database.
It creates all tables, triggers, stored procedures, views, and sample data.

Usage:
    python init_db.py
"""

import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123",
}

def run():
    # --- Connect WITHOUT database (to create it) ---
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Dropping and creating database...")
    cursor.execute("DROP DATABASE IF EXISTS banking_system")
    cursor.execute("CREATE DATABASE banking_system")
    cursor.execute("USE banking_system")

    # ---- TABLES ----
    print("Creating tables...")

    cursor.execute("""
        CREATE TABLE users (
            user_id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE accounts (
            account_id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            balance DECIMAL(15,2) DEFAULT 0.00,
            CONSTRAINT chk_balance_non_negative CHECK (balance >= 0),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE transactions (
            transaction_id INT PRIMARY KEY AUTO_INCREMENT,
            account_id INT NOT NULL,
            type ENUM('DEPOSIT','WITHDRAW') NOT NULL,
            amount DECIMAL(15,2) NOT NULL,
            status ENUM('SUCCESS','FAILED') NOT NULL DEFAULT 'SUCCESS',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_txn_amount_positive CHECK (amount > 0),
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE loans (
            loan_id INT PRIMARY KEY AUTO_INCREMENT,
            user_id INT NOT NULL,
            account_id INT NOT NULL,
            loan_amount DECIMAL(15,2) NOT NULL,
            remaining_amount DECIMAL(15,2) NOT NULL,
            interest_rate DECIMAL(5,2) NOT NULL,
            start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            status ENUM('ACTIVE','PAID') DEFAULT 'ACTIVE',
            CONSTRAINT chk_loan_amount_positive CHECK (loan_amount > 0),
            CONSTRAINT chk_remaining_non_negative CHECK (remaining_amount >= 0),
            CONSTRAINT chk_interest_non_negative CHECK (interest_rate >= 0),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE loan_payments (
            payment_id INT PRIMARY KEY AUTO_INCREMENT,
            loan_id INT NOT NULL,
            amount_paid DECIMAL(15,2) NOT NULL,
            payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT chk_payment_positive CHECK (amount_paid > 0),
            FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
        )
    """)

    # ---- INDEXES ----
    print("Creating indexes...")
    cursor.execute("CREATE INDEX idx_transactions_account ON transactions(account_id)")
    cursor.execute("CREATE INDEX idx_loans_user ON loans(user_id)")
    cursor.execute("CREATE INDEX idx_payments_loan ON loan_payments(loan_id)")
    cursor.execute("CREATE INDEX idx_accounts_user ON accounts(user_id)")

    # ---- TRIGGERS ----
    print("Creating triggers...")

    cursor.execute("""
        CREATE TRIGGER trg_before_withdrawal_check
        BEFORE INSERT ON transactions
        FOR EACH ROW
        BEGIN
            DECLARE current_bal DECIMAL(15,2);
            IF NEW.type = 'WITHDRAW' AND NEW.status = 'SUCCESS' THEN
                SELECT balance INTO current_bal
                FROM accounts
                WHERE account_id = NEW.account_id
                FOR UPDATE;
                IF current_bal IS NULL THEN
                    SIGNAL SQLSTATE '45000'
                    SET MESSAGE_TEXT = 'Account does not exist';
                END IF;
                IF current_bal < NEW.amount THEN
                    SET NEW.status = 'FAILED';
                END IF;
            END IF;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER trg_after_transaction_balance
        AFTER INSERT ON transactions
        FOR EACH ROW
        BEGIN
            IF NEW.status = 'SUCCESS' THEN
                IF NEW.type = 'DEPOSIT' THEN
                    UPDATE accounts
                    SET balance = balance + NEW.amount
                    WHERE account_id = NEW.account_id;
                ELSEIF NEW.type = 'WITHDRAW' THEN
                    UPDATE accounts
                    SET balance = balance - NEW.amount
                    WHERE account_id = NEW.account_id;
                END IF;
            END IF;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER trg_auto_loan_paid
        BEFORE UPDATE ON loans
        FOR EACH ROW
        BEGIN
            IF NEW.remaining_amount = 0 AND OLD.remaining_amount > 0 THEN
                SET NEW.status = 'PAID';
            END IF;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER trg_prevent_loan_overpayment
        BEFORE INSERT ON loan_payments
        FOR EACH ROW
        BEGIN
            DECLARE remaining DECIMAL(15,2);
            SELECT remaining_amount INTO remaining
            FROM loans
            WHERE loan_id = NEW.loan_id
            FOR UPDATE;
            IF remaining IS NULL THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Loan does not exist';
            END IF;
            IF NEW.amount_paid > remaining THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Payment exceeds remaining loan balance';
            END IF;
        END
    """)

    # ---- STORED PROCEDURE ----
    print("Creating stored procedure...")

    cursor.execute("""
        CREATE PROCEDURE sp_transfer_money(
            IN p_from_acc INT,
            IN p_to_acc INT,
            IN p_amount DECIMAL(15,2)
        )
        BEGIN
            DECLARE sender_balance DECIMAL(15,2);

            IF p_amount <= 0 THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Transfer amount must be positive';
            END IF;

            IF p_from_acc = p_to_acc THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Cannot transfer to the same account';
            END IF;

            START TRANSACTION;

            SELECT balance INTO sender_balance
            FROM accounts
            WHERE account_id = p_from_acc
            FOR UPDATE;

            IF sender_balance IS NULL THEN
                ROLLBACK;
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Sender account does not exist';
            END IF;

            IF sender_balance < p_amount THEN
                ROLLBACK;
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Insufficient balance for transfer';
            END IF;

            UPDATE accounts SET balance = balance - p_amount
            WHERE account_id = p_from_acc;

            UPDATE accounts SET balance = balance + p_amount
            WHERE account_id = p_to_acc;

            COMMIT;
        END
    """)

    # ---- VIEWS ----
    print("Creating views...")

    cursor.execute("""
        CREATE VIEW v_account_summary AS
        SELECT u.user_id, u.username, a.account_id, a.balance
        FROM users u
        JOIN accounts a ON u.user_id = a.user_id
    """)

    cursor.execute("""
        CREATE VIEW v_loan_overview AS
        SELECT l.loan_id, u.username, l.account_id, l.loan_amount,
               l.remaining_amount, l.interest_rate, l.start_date, l.status
        FROM loans l
        JOIN users u ON l.user_id = u.user_id
    """)

    cursor.execute("""
        CREATE VIEW v_monthly_transactions AS
        SELECT
            YEAR(created_at)  AS txn_year,
            MONTH(created_at) AS txn_month,
            COUNT(*)          AS total_transactions,
            SUM(CASE WHEN type = 'DEPOSIT'  AND status = 'SUCCESS' THEN amount ELSE 0 END) AS total_deposits,
            SUM(CASE WHEN type = 'WITHDRAW' AND status = 'SUCCESS' THEN amount ELSE 0 END) AS total_withdrawals,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count
        FROM transactions
        GROUP BY YEAR(created_at), MONTH(created_at)
    """)

    # User financial overview — demonstrates GROUP BY, SUM, COUNT, JOIN
    cursor.execute("""
        CREATE VIEW v_user_financial_overview AS
        SELECT
            u.user_id,
            u.username,
            COUNT(DISTINCT a.account_id) AS total_accounts,
            COALESCE(SUM(a.balance), 0) AS total_balance,
            (SELECT COUNT(*) FROM transactions t2
             JOIN accounts a2 ON t2.account_id = a2.account_id
             WHERE a2.user_id = u.user_id AND t2.status = 'SUCCESS') AS successful_transactions,
            (SELECT COUNT(*) FROM loans l2
             WHERE l2.user_id = u.user_id AND l2.status = 'ACTIVE') AS active_loans,
            (SELECT COALESCE(SUM(l3.remaining_amount), 0) FROM loans l3
             WHERE l3.user_id = u.user_id) AS total_loan_remaining
        FROM users u
        LEFT JOIN accounts a ON u.user_id = a.user_id
        GROUP BY u.user_id, u.username
    """)

    # Loan status summary — demonstrates GROUP BY, COUNT, SUM, HAVING
    cursor.execute("""
        CREATE VIEW v_loan_status_summary AS
        SELECT
            u.user_id,
            u.username,
            l.status,
            COUNT(*) AS loan_count,
            SUM(l.loan_amount) AS total_amount,
            SUM(l.loan_amount * l.interest_rate / 100) AS total_interest,
            SUM(l.remaining_amount) AS total_remaining
        FROM loans l
        JOIN users u ON l.user_id = u.user_id
        GROUP BY u.user_id, u.username, l.status
        HAVING COUNT(*) >= 1
    """)

    conn.commit()

    # ---- DONE ----
    cursor.close()
    conn.close()
    print()
    print("=" * 50)
    print("  Database 'banking_system' initialized!")
    print("  Tables, triggers, views, and procedure created.")
    print()
    print("  Now run: python app.py")
    print("  Then open: http://127.0.0.1:5000/")
    print("  Register a new account to get started.")
    print("=" * 50)

if __name__ == "__main__":
    run()
