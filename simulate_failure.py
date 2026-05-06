import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123",
    "database": "banking_system"
}

def simulate_failure_recovery():
    print("--- Simulating Transaction Failure & Recovery ---")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    try:
        # Get an account to test on
        cursor.execute("SELECT account_id, balance FROM accounts LIMIT 2")
        accounts = cursor.fetchall()
        
        if len(accounts) < 2:
            print("Need at least 2 accounts to run simulation.")
            return
            
        acc1 = accounts[0]
        acc2 = accounts[1]
        
        print(f"Initial State:")
        print(f"Account 1 ({acc1['account_id']}) Balance: {acc1['balance']}")
        print(f"Account 2 ({acc2['account_id']}) Balance: {acc2['balance']}")
        print("-" * 40)

        # START TRANSACTION
        print("1. START TRANSACTION")
        cursor.execute("START TRANSACTION")

        # Update 1
        print("2. Deducting 2000 from Account 1...")
        cursor.execute("UPDATE accounts SET balance = balance - 2000 WHERE account_id = %s", (acc1['account_id'],))
        
        # Savepoint
        print("3. Creating SAVEPOINT safe_point...")
        cursor.execute("SAVEPOINT safe_point")

        # Update 2
        print("4. Adding 2000 to Account 2...")
        cursor.execute("UPDATE accounts SET balance = balance + 2000 WHERE account_id = %s", (acc2['account_id'],))
        
        # Simulate Error
        print("5. 🚨 ERROR SIMULATED! Receiver account rejected transfer.")
        print("6. Rolling back to safe_point...")
        cursor.execute("ROLLBACK TO safe_point")
        
        # Since we rolled back to safe_point, the addition is undone. 
        # But the deduction is STILL active. To ensure full recovery, we must abort completely.
        print("7. Aborting entire transaction to prevent partial funds loss...")
        cursor.execute("ROLLBACK")
        
        print("-" * 40)
        
        # Verify final state
        cursor.execute("SELECT account_id, balance FROM accounts WHERE account_id IN (%s, %s)", 
                       (acc1['account_id'], acc2['account_id']))
        final_accounts = cursor.fetchall()
        
        print(f"Final State (Fully Recovered):")
        for a in final_accounts:
            print(f"Account {a['account_id']} Balance: {a['balance']}")
            
        print("\nSuccess! The system correctly recovered without losing funds.")

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    simulate_failure_recovery()
