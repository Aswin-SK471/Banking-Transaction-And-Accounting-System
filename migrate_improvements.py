"""
Migration: Add account_type to accounts, interest_amount to loans,
and create calculate_interest trigger.

Run this ONCE to apply improvements to the live database.
    python migrate_improvements.py

Safe to run multiple times - checks if columns/triggers already exist.
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
        # --- 1. Add account_type to accounts ---
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'banking_system' AND TABLE_NAME = 'accounts'
            AND COLUMN_NAME = 'account_type'
        """)
        if not cursor.fetchone():
            print("Adding account_type column to accounts...")
            cursor.execute("""
                ALTER TABLE accounts
                ADD COLUMN account_type VARCHAR(20) DEFAULT 'Savings'
            """)
            print("  [OK] account_type column added")
        else:
            print("  [OK] account_type column already exists")

        # --- 2. Add interest_amount to loans ---
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'banking_system' AND TABLE_NAME = 'loans'
            AND COLUMN_NAME = 'interest_amount'
        """)
        if not cursor.fetchone():
            print("Adding interest_amount column to loans...")
            cursor.execute("""
                ALTER TABLE loans
                ADD COLUMN interest_amount DECIMAL(12,2)
            """)
            # Backfill existing loans
            cursor.execute("""
                UPDATE loans
                SET interest_amount = loan_amount * interest_rate / 100
                WHERE interest_amount IS NULL
            """)
            print("  [OK] interest_amount column added and backfilled")
        else:
            print("  [OK] interest_amount column already exists")

        # --- 3. Create calculate_interest trigger ---
        cursor.execute("""
            SELECT TRIGGER_NAME FROM INFORMATION_SCHEMA.TRIGGERS
            WHERE TRIGGER_SCHEMA = 'banking_system'
            AND TRIGGER_NAME = 'trg_calculate_interest'
        """)
        if not cursor.fetchone():
            print("Creating calculate_interest trigger...")
            cursor.execute("""
                CREATE TRIGGER trg_calculate_interest
                BEFORE INSERT ON loans
                FOR EACH ROW
                SET NEW.interest_amount = NEW.loan_amount * NEW.interest_rate / 100
            """)
            print("  [OK] trigger created")
        else:
            print("  [OK] trigger already exists")

        conn.commit()
        print()
        print("=" * 50)
        print("  Migration complete!")
        print("  - accounts.account_type added")
        print("  - loans.interest_amount added + trigger")
        print("=" * 50)

    except mysql.connector.Error as e:
        conn.rollback()
        print("Migration failed:", e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run()
