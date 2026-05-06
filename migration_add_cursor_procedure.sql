-- Migration: Add Calculate Total Balance Procedure (Cursor)
USE banking_system;

DROP PROCEDURE IF EXISTS calculate_total_balance;

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
