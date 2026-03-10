# SQL Concepts Demonstrated — Banking System

This document catalogs every advanced SQL / DBMS concept used in this project.

---

## 1. Triggers

**What:** Code that executes automatically BEFORE or AFTER a database event (INSERT, UPDATE, DELETE).

| Trigger | Type | Table | Purpose |
|---|---|---|---|
| `trg_before_withdrawal_check` | BEFORE INSERT | transactions | If a withdrawal exceeds balance, auto-downgrades status to FAILED |
| `trg_after_transaction_balance` | AFTER INSERT | transactions | Auto-updates account balance for successful deposits/withdrawals |
| `trg_auto_loan_paid` | BEFORE UPDATE | loans | Auto-sets status to PAID when remaining_amount reaches 0 |
| `trg_prevent_loan_overpayment` | BEFORE INSERT | loan_payments | Blocks payments exceeding remaining loan balance |

**DBMS concept:** Triggers enforce business rules at the database level, ensuring data integrity even if application code has bugs.

---

## 2. Stored Procedures

**What:** Pre-compiled SQL routines stored in the database that can be called by name.

| Procedure | Parameters | Purpose |
|---|---|---|
| `sp_transfer_money` | from_acc, to_acc, amount | Atomically transfers money between two accounts |

**Key features:** Uses `START TRANSACTION` / `COMMIT` / `ROLLBACK`, `FOR UPDATE` row locking, and `SIGNAL SQLSTATE` for error handling.

**DBMS concept:** Encapsulates complex multi-step operations, ensures ACID compliance, and reduces network round-trips.

---

## 3. Views

**What:** Virtual tables defined by a SELECT query. They simplify complex queries and provide abstraction.

| View | Purpose | Key SQL Features |
|---|---|---|
| `v_account_summary` | Joins users + accounts for combined display | JOIN |
| `v_loan_overview` | Joins users + loans for loan display with username | JOIN |
| `v_monthly_transactions` | GROUP BY year/month with SUM/COUNT aggregates | GROUP BY, SUM, COUNT, CASE |
| `v_user_financial_overview` | Per-user summary: accounts, balance, loans, transactions | GROUP BY, COUNT DISTINCT, subqueries, LEFT JOIN |
| `v_loan_status_summary` | Loan counts/amounts grouped by user and status | GROUP BY, SUM, HAVING |

**DBMS concept:** Views provide a layer of abstraction, security (can expose limited columns), and query reusability.

---

## 4. CHECK Constraints

**What:** Rules that restrict the values allowed in a column.

| Table | Constraint | Rule |
|---|---|---|
| accounts | `chk_balance_non_negative` | `balance >= 0` |
| transactions | `chk_txn_amount_positive` | `amount > 0` |
| loans | `chk_loan_amount_positive` | `loan_amount > 0` |
| loans | `chk_remaining_non_negative` | `remaining_amount >= 0` |
| loans | `chk_interest_non_negative` | `interest_rate >= 0` |
| loan_payments | `chk_payment_positive` | `amount_paid > 0` |

**DBMS concept:** CHECK constraints are declarative integrity rules that the database enforces automatically.

---

## 5. Indexes

**What:** Data structures that speed up query performance by allowing faster lookups.

| Index | Table | Column(s) | Why |
|---|---|---|---|
| `idx_transactions_account` | transactions | account_id | Frequent filtering by account |
| `idx_loans_user` | loans | user_id | Per-user loan lookups |
| `idx_payments_loan` | loan_payments | loan_id | Payment history per loan |
| `idx_accounts_user` | accounts | user_id | Login/dashboard queries |

**DBMS concept:** Indexes trade storage space for query speed — essential for read-heavy applications.

---

## 6. Foreign Keys

**What:** Constraints that enforce referential integrity between tables.

| Child Table | FK Column | References |
|---|---|---|
| accounts | user_id | users(user_id) |
| transactions | account_id | accounts(account_id) |
| loans | user_id | users(user_id) |
| loans | account_id | accounts(account_id) |
| loan_payments | loan_id | loans(loan_id) |

**DBMS concept:** Foreign keys prevent orphan records and maintain relational integrity.

---

## 7. ENUM Data Type

**What:** A column type that restricts values to a predefined set.

| Table | Column | Values |
|---|---|---|
| transactions | type | DEPOSIT, WITHDRAW |
| transactions | status | SUCCESS, FAILED |
| loans | status | ACTIVE, PAID |

**DBMS concept:** ENUMs enforce domain constraints at the column level.

---

## 8. Aggregate Functions & GROUP BY

**Used in:** Dashboard queries, monthly reports, loan analytics, views

| Function | Usage |
|---|---|
| `SUM()` | Total deposits, withdrawals, loan amounts |
| `COUNT()` | Transaction counts, active/paid loan counts |
| `COUNT(DISTINCT)` | Unique account counts per user |
| `COALESCE()` | Default 0 for NULL aggregates |
| `CASE WHEN` | Conditional aggregation (e.g., only SUCCESS deposits) |
| `GROUP BY` | Monthly grouping, per-user summaries, loan status grouping |
| `HAVING` | Filter groups (e.g., users with >= 1 loan) |
| Subqueries | Correlated subqueries in v_user_financial_overview |

**DBMS concept:** Aggregate functions with GROUP BY enable analytical reporting directly in SQL.

---

## 9. Transaction Management (ACID)

**Used in:** Stored procedure `sp_transfer_money`

| Property | How Enforced |
|---|---|
| **Atomicity** | START TRANSACTION + COMMIT/ROLLBACK |
| **Consistency** | CHECK constraints + triggers |
| **Isolation** | FOR UPDATE row-level locks |
| **Durability** | MySQL InnoDB engine default |

**DBMS concept:** ACID properties guarantee reliable database operations, especially for financial systems.

---

## 10. Normalization

The schema is fully normalized to **3NF** (Third Normal Form). See `normalization.md` for the complete analysis.

---

## Summary

| Concept | Count | Location |
|---|---|---|
| Triggers | 4 | database.sql |
| Stored Procedures | 1 | database.sql |
| Views | 5 | init_db.py |
| CHECK Constraints | 6 | database.sql |
| Indexes | 4 | database.sql |
| Foreign Keys | 5 | database.sql |
| ENUM Types | 3 | database.sql |
| Aggregate Queries | 5+ | app.py |
| ACID Transactions | 1 | database.sql |
