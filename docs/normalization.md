# Normalization Analysis — Banking System

## Functional Dependencies

### users
- `user_id → username, email, password_hash`
- `username → user_id` (UNIQUE)
- `email → user_id` (UNIQUE)

### accounts
- `account_id → user_id, balance`

### transactions
- `transaction_id → account_id, type, amount, status, created_at`

### loans
- `loan_id → user_id, account_id, loan_amount, remaining_amount, interest_rate, start_date, status`

### loan_payments
- `payment_id → loan_id, amount_paid, payment_date`

---

## 1NF (First Normal Form) ✅

**Requirement:** All attributes must contain atomic (indivisible) values, and each row must be uniquely identifiable.

| Table | Atomic Values | Unique Rows | 1NF |
|---|---|---|---|
| users | ✅ All columns are single values | ✅ PK: user_id | ✅ |
| accounts | ✅ All columns are single values | ✅ PK: account_id | ✅ |
| transactions | ✅ All columns are single values | ✅ PK: transaction_id | ✅ |
| loans | ✅ All columns are single values | ✅ PK: loan_id | ✅ |
| loan_payments | ✅ All columns are single values | ✅ PK: payment_id | ✅ |

**Conclusion:** All tables satisfy 1NF — no repeating groups, no multi-valued attributes.

---

## 2NF (Second Normal Form) ✅

**Requirement:** Must be in 1NF + no partial dependencies (non-key attributes must depend on the entire primary key, not part of it).

Since all tables use single-column primary keys (auto-increment INT), partial dependencies are **impossible** — every non-key attribute depends on the entire (single-column) PK.

| Table | PK Type | Partial Dependencies | 2NF |
|---|---|---|---|
| users | Single column | None possible | ✅ |
| accounts | Single column | None possible | ✅ |
| transactions | Single column | None possible | ✅ |
| loans | Single column | None possible | ✅ |
| loan_payments | Single column | None possible | ✅ |

**Conclusion:** All tables satisfy 2NF.

---

## 3NF (Third Normal Form) ✅

**Requirement:** Must be in 2NF + no transitive dependencies (non-key attributes must not depend on other non-key attributes).

### Analysis per table:

**users:** `user_id → username, email, password_hash`. No non-key attribute determines another non-key attribute. ✅

**accounts:** `account_id → user_id, balance`. `user_id` is a FK reference, not a transitive dependency — `balance` does not depend on `user_id`, it depends on `account_id`. ✅

**transactions:** `transaction_id → account_id, type, amount, status, created_at`. All non-key attributes depend directly on `transaction_id`. `status` is determined by the transaction itself, not derived from another non-key attribute. ✅

**loans:** `loan_id → user_id, account_id, loan_amount, remaining_amount, interest_rate, start_date, status`.
- `remaining_amount` might _seem_ derivable from `loan_amount` and payments, but it is stored independently and updated by payments. It is not determined by another non-key column — it tracks state over time. ✅
- `status` is updated by a trigger when `remaining_amount = 0`. Although it correlates with `remaining_amount`, it is maintained as an independent attribute for query efficiency. ✅

**loan_payments:** `payment_id → loan_id, amount_paid, payment_date`. All attributes depend directly on `payment_id`. ✅

**Conclusion:** All tables satisfy 3NF — no transitive dependencies exist.

---

## Summary

| Normalization Level | Status | Explanation |
|---|---|---|
| **1NF** | ✅ Satisfied | All atomic values, unique PKs, no repeating groups |
| **2NF** | ✅ Satisfied | Single-column PKs eliminate partial dependencies |
| **3NF** | ✅ Satisfied | No transitive dependencies between non-key attributes |

The database schema is fully normalized to Third Normal Form (3NF).
