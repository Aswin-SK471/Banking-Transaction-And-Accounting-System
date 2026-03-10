# ER Diagram — Banking System

## Entity-Relationship Diagram

```mermaid
erDiagram
    USERS {
        INT user_id PK
        VARCHAR username UK
        VARCHAR email UK
        VARCHAR password_hash
    }

    ACCOUNTS {
        INT account_id PK
        INT user_id FK
        DECIMAL balance
    }

    TRANSACTIONS {
        INT transaction_id PK
        INT account_id FK
        ENUM type
        DECIMAL amount
        ENUM status
        DATETIME created_at
    }

    LOANS {
        INT loan_id PK
        INT user_id FK
        INT account_id FK
        DECIMAL loan_amount
        DECIMAL remaining_amount
        DECIMAL interest_rate
        DATETIME start_date
        ENUM status
    }

    LOAN_PAYMENTS {
        INT payment_id PK
        INT loan_id FK
        DECIMAL amount_paid
        DATETIME payment_date
    }

    USERS ||--o{ ACCOUNTS : "has"
    ACCOUNTS ||--o{ TRANSACTIONS : "records"
    USERS ||--o{ LOANS : "applies for"
    ACCOUNTS ||--o{ LOANS : "linked to"
    LOANS ||--o{ LOAN_PAYMENTS : "receives"
```

## Relational Schema

| Table | Primary Key | Foreign Keys | Description |
|---|---|---|---|
| `users` | `user_id` | — | System users with credentials |
| `accounts` | `account_id` | `user_id → users` | Bank accounts with balances |
| `transactions` | `transaction_id` | `account_id → accounts` | Deposit/withdrawal records |
| `loans` | `loan_id` | `user_id → users`, `account_id → accounts` | Loan records with interest tracking |
| `loan_payments` | `payment_id` | `loan_id → loans` | Loan repayment records |

## Relationships

- **USERS → ACCOUNTS**: One-to-Many (one user can have multiple accounts; currently one is auto-created)
- **ACCOUNTS → TRANSACTIONS**: One-to-Many (one account has many transactions)
- **USERS → LOANS**: One-to-Many (one user can have multiple loans)
- **ACCOUNTS → LOANS**: One-to-Many (loans are linked to a specific account)
- **LOANS → LOAN_PAYMENTS**: One-to-Many (one loan has many payment records)
