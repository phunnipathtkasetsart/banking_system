# Transaction proof · shot list

The most important folder: it proves the atomic transactions and the rollback. Take these **in order, in one sitting**, and don't make other changes in between. "Before" and "after" shots use **Admin → Data explorer → Overview → Rollback check**; select **Refresh** before each one.

Tip: keep two browser windows open, one logged in as `admin` and a private window logged in as `alice`.

## 18. Successful transfer (SQL commit, then Mongo sync)

- [ ] **`18a-success-before.png`**: Rollback check panel. Show alice's and bob's balances and the `banking_transaction` row count.
- [ ] **`18b-success-receipt.png`**: As alice: **Transfer** ฿1,000 from Main savings to bob → **Send money**. Show the receipt with its DEBIT and CREDIT ledger lines.
- [ ] **`18c-success-after.png`**: Rollback check after **Refresh**. Show alice −1,000, bob +1,000, and the transaction count +1.
- [ ] **`18d-success-mongo-sync.png`**: **Data explorer → `notifications`** → Field `title` = `Money received` → **Find**. Show the notification written to MongoDB after the commit.

## 19. Rollback (simulated failure)

- [ ] **`19a-rollback-before.png`**: Rollback check after **Refresh** (same numbers as 18c).
- [ ] **`19b-rollback-error.png`**: As alice: **Transfer** ฿500 to bob with **Simulate failure (demo)** ticked → **Send money**. Show the red message "Transfer failed and was rolled back: Simulated system failure…".
- [ ] **`19c-rollback-after.png`**: Rollback check after **Refresh**. Show balances and counts **unchanged** from 19a, and the new failed attempt marked "rolled back" on the right.
- [ ] **`19d-rollback-log.png`**: **Data explorer → `activity_logs`** → Field `status` = `FAILED` → **Find**. Show the raw JSON with `"rolled_back": true` and the reason.

## 20. Business-rule rejections (also rolled back)

- [ ] **`20a-insufficient-funds.png`**: As bob: **Transfer** ฿99,999,999 to alice. Show "Insufficient funds." in the red message.
- [ ] **`20b-frozen-account.png`**: As admin, freeze bob's Main savings. As alice, transfer ฿10 to it. Show "Account … is frozen." Then set bob's account back to **Active**.

## 21. Database constraint

- [ ] **`21-check-constraint.png`**: **Data explorer → `banking_account`**. Show the Constraints card with the `CHECK` that keeps `balance >= 0`. This is the database's own guard if the app's checks were ever bypassed.

## Optional terminal proof

To show the same before/after from `psql`, run this before 19b and again after it, and save the two results as `19e-psql-before.png` and `19f-psql-after.png`:

```bash
docker compose exec db psql -U digibank -d digibank -c "SELECT account_number, balance FROM banking_account ORDER BY id;" -c "SELECT count(*) FROM banking_transaction;"
```
