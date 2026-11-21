# SQL features (PostgreSQL) · shot list

Save each screenshot in this folder with the filename shown. Do them in order. Capture the green or red message bar whenever a step changes data. Tick each box when done.

## Customer (log in as `alice`, except shot 01)

- [ ] **`01-register.png`**: Register a customer
  Log out → **Open an account** → register `dana` → submit.
  Show: dana's overview with the new **Main savings** account (฿0.00) and the success message.

- [ ] **`02-customer-overview.png`**: Customer overview with account cards
  Log in as alice → **Overview**.
  Show: total balance, account cards, recent transactions.

- [ ] **`03-account-open-rename-close.png`**: Open, rename and close an account
  **Accounts → Open an account** → Fixed deposit "Holiday" → open it → **Rename** to "Holiday 2027" → **Close account** → confirm.
  Show: the Accounts page with the message "Account … deleted." (an empty account with no history is removed).

- [ ] **`04-deposit-withdraw.png`**: Deposit and withdraw
  **Deposit** ฿2,000 "Salary" to Main savings, then **Withdraw** ฿500.
  Show: the withdrawal receipt with its DEBIT ledger line.

- [ ] **`05-statement.png`**: Account statement (passbook)
  **Accounts → Main savings**.
  Show: passbook rows with withdrawal, deposit and running balance.

- [ ] **`06-saved-payees.png`**: Saved payees
  **Saved payees → Add a payee** → bob's account number, "Bob" → then **Rename** to "Bobby".
  Show: the payee list with "Bobby" and the success message.

- [ ] **`07-transaction-history.png`**: Transaction history (joined query)
  **Transactions**.
  Show: reference, type, from → to account numbers, amount, status.

## Admin (log in as `admin`)

- [ ] **`08-admin-users.png`**: User management
  **Customers & staff → Add a user** → create `erin` → **Edit** phone → **Deactivate** → **Delete** → confirm. Then open **alice → Delete** → confirm.
  Show: the error that alice can't be deleted because her accounts have history (protected by foreign key).

- [ ] **`09-admin-freeze.png`**: Freeze an account
  **Accounts** → bob's Main savings → **Freeze or edit** → status Frozen → save.
  Show: the FROZEN chip and greyed card.
  **Then set it back to Active**, or later transfers to bob will fail.

- [ ] **`10-admin-counter-deposit.png`**: Counter deposit
  Any active account → **Counter deposit or withdrawal** → Deposit ฿1,000 → **Record it**.
  Show: the passbook with the new line and the success message.

- [ ] **`11-admin-reverse.png`**: Reverse a transaction
  **Transactions** → open alice's ฿2,000 "Salary" deposit (from shot 04) → **Reverse transaction** → reason "Duplicate deposit" → submit.
  Show: the new REVERSAL receipt, which names the original transaction it reverses.

- [ ] **`12-admin-dashboard.png`**: Admin dashboard
  **Dashboard**.
  Show: the day sheet with its PostgreSQL and MongoDB panels.
