# Screenshot shot list

Save each screenshot into this folder with the exact filename below. The number prefix keeps files in reading order. Tick each one off as you go.

## Before you start

1. Reset to clean demo data so the numbers in every screenshot match:
   ```bash
   docker compose down -v
   docker compose up -d --build
   docker compose exec web python manage.py seed_demo
   ```
2. Use a browser window about 1440 × 900, zoom 100%.
3. Logins: `admin / Admin@12345`, `alice / Customer@123`, `bob / Customer@123`.
4. Whenever a step changes data, capture the success message (the green or red bar) in the same shot.

---

## A. SQL features (PostgreSQL)

| ✓ | File | Login | Steps | Must be visible |
|---|---|---|---|---|
| ☐ | `01-sql-register.png` | (signed out) | Log in page → **Open an account** → fill in a new user, e.g. `dana` | Filled-in registration form |
| ☐ | `02-sql-register-done.png` | dana | Submit the form | Overview with the new **Main savings** account (฿0.00) and the success message |
| ☐ | `03-sql-customer-overview.png` | alice | **Overview** | Total balance, account cards, recent transactions |
| ☐ | `04-sql-open-account.png` | alice | **Accounts → Open an account** → Fixed deposit, nickname "Holiday" → submit | New card on the Accounts page |
| ☐ | `05-sql-rename-account.png` | alice | Open the "Holiday" card → **Rename** → "Holiday 2027" | Updated nickname plus the success message |
| ☐ | `06-sql-deposit.png` | alice | **Deposit** → Main savings, 2,000, "Salary" | Receipt page with ledger line CREDIT |
| ☐ | `07-sql-withdraw.png` | alice | **Withdraw** → Main savings, 500 | Receipt with ledger line DEBIT |
| ☐ | `08-sql-statement.png` | alice | Accounts → Main savings | Passbook with withdrawal / deposit / running balance |
| ☐ | `09-sql-payee-add.png` | alice | **Saved payees → Add a payee** → bob's account number, "Bob" | Payee list with the new row |
| ☐ | `10-sql-payee-edit-delete.png` | alice | Rename the payee, then open **Remove** | Confirm-remove page |
| ☐ | `11-sql-close-account.png` | alice | "Holiday 2027" → **Close account** → confirm | Message "… deleted" (empty account with no history is removed) |
| ☐ | `12-sql-transaction-history.png` | alice | **Transactions** | Joined list: reference, type, from → to account numbers, amount, status |
| ☐ | `13-sql-admin-users.png` | admin | **Customers & staff** | User list with roles, account counts, active status |
| ☐ | `14-sql-admin-create-user.png` | admin | **Add a user** → create `erin` (Customer) | User detail page for erin |
| ☐ | `15-sql-admin-edit-user.png` | admin | erin → **Edit** → change phone → save, then **Deactivate** | Status "Inactive" plus the success message |
| ☐ | `16-sql-admin-delete-user.png` | admin | erin → **Delete** → confirm | "User erin deleted." on the user list |
| ☐ | `17-sql-admin-delete-blocked.png` | admin | alice → **Delete** → confirm | Error: user has history, protected by FK, deactivate instead |
| ☐ | `18-sql-admin-freeze.png` | admin | **Accounts** → bob's Main savings → **Freeze or edit** → status Frozen. **After the screenshot, set it back to Active**, or the transfers to bob below will fail | Account with FROZEN chip (greyed card) |
| ☐ | `19-sql-admin-teller.png` | admin | Any active account → Counter deposit 1,000 | Passbook with the new line |
| ☐ | `20-sql-admin-reverse.png` | admin | **Transactions** → open a transfer → **Reverse transaction** → reason → submit | New REVERSAL receipt; original now REVERSED |
| ☐ | `21-sql-admin-dashboard.png` | admin | **Dashboard** | Day sheet with the PostgreSQL and MongoDB panels |

## B. NoSQL features (MongoDB)

| ✓ | File | Login | Steps | Must be visible |
|---|---|---|---|---|
| ☐ | `22-nosql-draft-create.png` | alice | **Transfer** → fill in to bob, 300 → **Save as draft** | Drafts list with the new draft |
| ☐ | `23-nosql-draft-edit.png` | alice | Draft → **Edit** → amount 350 → save | Updated amount |
| ☐ | `24-nosql-draft-send.png` | alice | Draft → **Send now** | Receipt; Drafts list now empty |
| ☐ | `25-nosql-notifications.png` | bob | **Notifications** | Unread "Money received" plus older items, unread count in sidebar |
| ☐ | `26-nosql-notifications-read.png` | bob | **Mark as read** on one, **Dismiss** another | Updated list |
| ☐ | `27-nosql-broadcast.png` | admin | **Broadcast** → all customers, "Maintenance Saturday 02:00" | "Sent to N user(s)." |
| ☐ | `28-nosql-ticket-create.png` | alice | **Support → New ticket** → "Card blocked", Card, High | Ticket thread with the first message |
| ☐ | `29-nosql-ticket-reply.png` | admin | **Support desk** → open the ticket → reply, status In progress | Staff reply bubble and status chip |
| ☐ | `30-nosql-ticket-close-delete.png` | alice | Ticket → **Close ticket**, then **Delete** confirm page | Closed status / confirm page |
| ☐ | `31-nosql-my-activity.png` | alice | **My activity** | LOGIN, TRANSFER, DEPOSIT… with metadata |
| ☐ | `32-nosql-admin-logs.png` | admin | **Activity logs** → filter Result = Failed | Failed attempts with reasons |
| ☐ | `33-nosql-admin-log-review.png` | admin | A log → **Review** → tick Reviewed, add a note → save | Row shows "Reviewed" plus the note |

## C. Transaction proof (the most important section)

Take these in order, without doing anything else in between.

| ✓ | File | Login | Steps | Must be visible |
|---|---|---|---|---|
| ☐ | `34-txn-success-before.png` | admin | **Data explorer** → Overview → Rollback check | alice and bob balances, `banking_transaction` row count |
| ☐ | `35-txn-success-form.png` | alice | Transfer → Main savings → bob's account, 1,000 → **Send money** | Receipt with DEBIT and CREDIT ledger lines |
| ☐ | `36-txn-success-after.png` | admin | Data explorer → Overview → Refresh | alice −1,000, bob +1,000, transaction count +1 |
| ☐ | `37-txn-success-mongo-sync.png` | admin | Data explorer → `notifications` → filter `title = Money received` | Notification written after the commit |
| ☐ | `38-txn-rollback-before.png` | admin | Data explorer → Overview → Refresh | Balances and counts (same as 36) |
| ☐ | `39-txn-rollback-form.png` | alice | Transfer 500 to bob with **Simulate failure (demo)** ticked → **Send money** | Red message "Transfer failed and was rolled back: Simulated system failure…" |
| ☐ | `40-txn-rollback-after.png` | admin | Data explorer → Overview → Refresh | Balances and counts unchanged from 38; new failed attempt on the right with "rolled back" |
| ☐ | `41-txn-rollback-log.png` | admin | Data explorer → `activity_logs` → filter `status = FAILED` | Raw JSON with `"rolled_back": true` and the reason |
| ☐ | `42-txn-insufficient-funds.png` | bob | Transfer 99,999,999 to alice | "Insufficient funds." rolled-back message |
| ☐ | `43-txn-frozen-account.png` | alice | As admin, freeze bob's Main savings again; as alice, transfer 10 to it; then unfreeze it | "Account … is frozen." rolled-back message |
| ☐ | `44-txn-db-constraint.png` | admin | Data explorer → `banking_account` | Constraints card showing the `CHECK` on `balance >= 0` |

Optional, for extra proof from a terminal: run the same query before and after shot 39 and screenshot both:

```bash
docker compose exec db psql -U digibank -d digibank -c "SELECT account_number, balance FROM banking_account ORDER BY id;" -c "SELECT count(*) FROM banking_transaction;"
```

## D. Documentation

| ✓ | File | Source |
|---|---|---|
| ☐ | `45-doc-architecture.png` | `docs/diagrams/architecture.md` rendered on GitHub |
| ☐ | `46-doc-er-diagram.png` | `docs/diagrams/er-diagram.md` |
| ☐ | `47-doc-nosql-schema.png` | `docs/diagrams/nosql-schema.md` |
| ☐ | `48-doc-transfer-flow.png` | `docs/diagrams/transfer-flow.md` |
| ☐ | `49-doc-data-explorer.png` | Admin → Data explorer → `users_user` (columns, constraints, raw rows) |
| ☐ | `50-doc-password-storage.png` | Admin → Password storage, after **Hash it twice** with a made-up value |
| ☐ | `51-doc-mobile.png` | Any customer page with the browser narrowed to phone width (optional) |
