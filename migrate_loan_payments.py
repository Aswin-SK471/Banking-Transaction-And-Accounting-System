"""
Migration: Add account_id and remaining_balance columns to loan_payments table.

Run this ONCE to fix the live database without losing existing data.
    python migrate_loan_payments.py

This is safe to run — it checks if columns already exist before adding them.
"""

import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123",
    "database": "banking_system",
}

def run():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        # Check which columns already exist
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'banking_system' AND TABLE_NAME = 'loan_payments'
        """)
        existing_columns = {row["COLUMN_NAME"] for row in cursor.fetchall()}
        print("Existing columns:", existing_columns)

        # Add account_id if missing
        if "account_id" not in existing_columns:
            print("Adding account_id column...")
            cursor.execute("""
                ALTER TABLE loan_payments
                ADD COLUMN account_id INT,
                ADD CONSTRAINT fk_loan_payment_account
                    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            """)
            print("  [OK] account_id column added")
        else:
            print("  [OK] account_id column already exists")

        # Add remaining_balance if missing
        if "remaining_balance" not in existing_columns:
            print("Adding remaining_balance column...")
            cursor.execute("""
                ALTER TABLE loan_payments
                ADD COLUMN remaining_balance DECIMAL(15,2)
            """)
            print("  [OK] remaining_balance column added")
        else:
            print("  [OK] remaining_balance column already exists")

        conn.commit()
        print()
        print("=" * 50)
        print("  Migration complete!")
        print("  loan_payments table now has account_id and remaining_balance.")
        print("  You can now use the Pay Loan feature.")
        print("=" * 50)

    except mysql.connector.Error as e:
        conn.rollback()
        print("Migration failed:", e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run()
