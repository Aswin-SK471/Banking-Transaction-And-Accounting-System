-- =====================================================
-- Banking Management System
-- Complete Schema with Triggers, Views, Procedures
-- =====================================================

DROP DATABASE IF EXISTS banking_system;
CREATE DATABASE banking_system;
USE banking_system;

-- =====================================================
-- TABLE: USERS
-- =====================================================
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    gmail VARCHAR(100) UNIQUE,
    aadhar_number VARCHAR(12) UNIQUE,
    phone VARCHAR(15) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    CONSTRAINT chk_aadhar CHECK (LENGTH(aadhar_number) = 12)
);

-- =====================================================
-- TABLE: ACCOUNTS
-- =====================================================
CREATE TABLE accounts (
    account_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    account_type VARCHAR(20) DEFAULT 'Savings',
    balance DECIMAL(15,2) DEFAULT 0.00,
    CONSTRAINT chk_balance_non_negative CHECK (balance >= 0),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- =====================================================
-- TABLE: TRANSACTIONS (Deposits & Withdrawals only)
-- =====================================================
CREATE TABLE transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    account_id INT NOT NULL,
    type ENUM('DEPOSIT','WITHDRAW') NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    status ENUM('SUCCESS','FAILED') NOT NULL DEFAULT 'SUCCESS',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_txn_amount_positive CHECK (amount > 0),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- =====================================================
-- TABLE: LOANS
-- =====================================================
CREATE TABLE loans (
    loan_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    account_id INT NOT NULL,
    loan_amount DECIMAL(15,2) NOT NULL,
    remaining_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    interest_amount DECIMAL(12,2),
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('ACTIVE','PAID') DEFAULT 'ACTIVE',
    CONSTRAINT chk_loan_amount_positive CHECK (loan_amount > 0),
    CONSTRAINT chk_remaining_non_negative CHECK (remaining_amount >= 0),
    CONSTRAINT chk_interest_non_negative CHECK (interest_rate >= 0),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- =====================================================
-- TABLE: LOAN PAYMENTS
-- =====================================================
CREATE TABLE loan_payments (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    loan_id INT NOT NULL,
    account_id INT NOT NULL,
    amount_paid DECIMAL(15,2) NOT NULL,
    remaining_balance DECIMAL(15,2) NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_payment_positive CHECK (amount_paid > 0),
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- =====================================================
-- INDEXES (speed up frequent queries)
-- =====================================================
-- Why: transactions are queried by account_id frequently
CREATE INDEX idx_transactions_account ON transactions(account_id);
-- Why: loans are queried by user_id for filtering
CREATE INDEX idx_loans_user ON loans(user_id);
-- Why: loan payments are queried by loan_id for history
CREATE INDEX idx_payments_loan ON loan_payments(loan_id);
-- Why: accounts are queried by user_id on every login
CREATE INDEX idx_accounts_user ON accounts(user_id);

-- =====================================================
-- TRIGGER 1: Prevent withdrawal if balance insufficient
-- =====================================================
-- DBMS Concept: BEFORE INSERT trigger enforces a business
-- rule at the database level — even if application code
-- has a bug, the DB itself prevents invalid withdrawals.
-- =====================================================
DELIMITER $$

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
            -- Auto-downgrade to FAILED instead of crashing
            SET NEW.status = 'FAILED';
        END IF;
    END IF;
END$$

DELIMITER ;

-- =====================================================
-- TRIGGER 2: Auto-update account balance after transaction
-- =====================================================
-- DBMS Concept: AFTER INSERT trigger automatically keeps
-- the accounts.balance in sync with successful transactions,
-- ensuring ACID consistency without relying on app code.
-- =====================================================
DELIMITER $$

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
END$$

DELIMITER ;

-- =====================================================
-- TRIGGER 3: Auto-set loan status to PAID
-- =====================================================
-- DBMS Concept: AFTER UPDATE trigger ensures data integrity —
-- when remaining_amount reaches 0, the loan is automatically
-- marked as PAID without relying on application logic.
-- =====================================================
DELIMITER $$

CREATE TRIGGER trg_auto_loan_paid
BEFORE UPDATE ON loans
FOR EACH ROW
BEGIN
    IF NEW.remaining_amount = 0 AND OLD.remaining_amount > 0 THEN
        SET NEW.status = 'PAID';
    END IF;
END$$

DELIMITER ;

-- =====================================================
-- TRIGGER 4: Prevent overpayment on loans
-- =====================================================
-- DBMS Concept: BEFORE INSERT trigger validates that a
-- loan payment does not exceed the remaining balance,
-- acting as a database-level constraint.
-- =====================================================
DELIMITER $$

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
END$$

DELIMITER ;

-- =====================================================
-- STORED PROCEDURE: Transfer Money Between Accounts
-- =====================================================
-- DBMS Concept: Stored procedures encapsulate complex
-- multi-step operations in the database. This procedure
-- uses explicit transaction control (START TRANSACTION /
-- COMMIT / ROLLBACK) to ensure ACID compliance — either
-- both accounts update or neither does.
-- =====================================================
DELIMITER $$

CREATE PROCEDURE sp_transfer_money(
    IN p_from_acc INT,
    IN p_to_acc INT,
    IN p_amount DECIMAL(15,2)
)
BEGIN
    DECLARE sender_balance DECIMAL(15,2);

    -- Validate amount
    IF p_amount <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Transfer amount must be positive';
    END IF;

    -- Same account check
    IF p_from_acc = p_to_acc THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cannot transfer to the same account';
    END IF;

    START TRANSACTION;

    -- Lock sender row and check balance
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

    -- Deduct from sender
    UPDATE accounts SET balance = balance - p_amount
    WHERE account_id = p_from_acc;

    -- Create a savepoint after successful deduction
    SAVEPOINT after_deduct;

    -- Credit to receiver
    UPDATE accounts SET balance = balance + p_amount
    WHERE account_id = p_to_acc;

    -- Check for failure condition: Receiver account does not exist
    IF ROW_COUNT() = 0 THEN
        -- If something goes wrong:
        ROLLBACK TO after_deduct;
        ROLLBACK; -- abort the entire transaction
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Receiver account does not exist';
    END IF;

    COMMIT;
END$$

DELIMITER ;

-- =====================================================
-- STORED PROCEDURE: Calculate Total Balance (Cursor)
-- =====================================================
DELIMITER $$

CREATE PROCEDURE calculate_total_balance()
BEGIN
    DECLARE done INT DEFAULT FALSE;
    DECLARE acc_balance DECIMAL(15,2);
    DECLARE total DECIMAL(15,2) DEFAULT 0;

    DECLARE cur CURSOR FOR SELECT balance FROM accounts;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;

    OPEN cur;

    read_loop: LOOP
        FETCH cur INTO acc_balance;
        IF done THEN
            LEAVE read_loop;
        END IF;
        SET total = total + acc_balance;
    END LOOP;

    CLOSE cur;

    SELECT total AS total_bank_balance;
END$$

DELIMITER ;

-- =====================================================
-- VIEW 1: Account Summary
-- =====================================================
-- DBMS Concept: Views provide a virtual table that joins
-- users and accounts, simplifying queries and providing
-- a clean abstraction layer.
-- =====================================================
CREATE VIEW v_account_summary AS
SELECT
    u.user_id,
    u.username,
    a.account_id,
    a.balance
FROM users u
JOIN accounts a ON u.user_id = a.user_id;

-- =====================================================
-- VIEW 2: Loan Overview
-- =====================================================
-- Joins users + loans for a complete loan picture
-- with username instead of just user_id.
-- =====================================================
CREATE VIEW v_loan_overview AS
SELECT
    l.loan_id,
    u.username,
    l.account_id,
    l.loan_amount,
    l.remaining_amount,
    l.interest_rate,
    l.start_date,
    l.status
FROM loans l
JOIN users u ON l.user_id = u.user_id;

-- =====================================================
-- VIEW 3: Monthly Transaction Summary
-- =====================================================
-- DBMS Concept: Uses GROUP BY with aggregate functions
-- (SUM, COUNT) to produce a monthly report. This
-- demonstrates analytical SQL capabilities.
-- =====================================================
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
ORDER BY txn_year DESC, txn_month DESC;

-- =====================================================
-- SAMPLE DATA
-- =====================================================
-- Sample users (password for both: password123)
-- Hashes generated with werkzeug.security.generate_password_hash
INSERT INTO users (username, email, gmail, aadhar_number, phone, password_hash) VALUES
('Alice', 'alice@mail.com', 'alice@gmail.com', '123456789012', '9876543210',
 'scrypt:32768:8:1$placeholder$0000000000000000000000000000000000000000000000000000000000000000'),
('Bob', 'bob@mail.com', 'bob@gmail.com', '987654321098', '8765432109',
 'scrypt:32768:8:1$placeholder$0000000000000000000000000000000000000000000000000000000000000000');

INSERT INTO accounts (user_id, balance) VALUES
(1, 5000.00),
(2, 8000.00);

-- =====================================================
-- END OF SETUP
-- =====================================================