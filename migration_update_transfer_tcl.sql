-- Migration: Update sp_transfer_money with full TCL (SAVEPOINT and ROLLBACK TO)
USE banking_system;

DROP PROCEDURE IF EXISTS sp_transfer_money;

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
