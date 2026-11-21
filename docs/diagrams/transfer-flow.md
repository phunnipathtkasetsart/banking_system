# Transfer workflow (transaction + rollback)

Phase 1 runs in one PostgreSQL transaction; any error rolls back every step. Phase 2 runs only after the SQL commit and writes all MongoDB side effects in one multi-document transaction. Code: `banking/services.py` → `transfer()`.

```mermaid
---
title: Transfer workflow · SQL transaction first, then cross-database sync to MongoDB
---
sequenceDiagram
    autonumber
    actor C as Customer
    participant V as Django view<br/>banking/views.py
    participant S as services.transfer()
    participant PG as PostgreSQL
    participant MG as MongoDB

    C->>V: POST /bank/transfer/ (from, to, amount)
    V->>S: transfer(actor, from_account_id, to_account_number, amount)

    rect rgb(219, 231, 243)
    Note over S,PG: Phase 1 · one ACID transaction (transaction.atomic)
    S->>PG: BEGIN
    S->>PG: SELECT … FOR UPDATE both accounts (ordered by id, avoids deadlock)
    S->>S: check owner · both ACTIVE · balance ≥ amount
    S->>PG: UPDATE sender balance − amount
    S->>PG: UPDATE receiver balance + amount
    S->>PG: INSERT banking_transaction (TRANSFER)
    S->>PG: INSERT 2 banking_transactionentry (DEBIT, CREDIT)
    end

    alt any step raised (insufficient funds · frozen account · simulated failure · CHECK violation)
        S->>PG: ROLLBACK (all updates and inserts undone)
        S->>MG: insert activity_logs {status: FAILED, rolled_back: true, reason}
        V-->>C: "Transfer failed and was rolled back: reason"
    else every step succeeded
        S->>PG: COMMIT
        rect rgb(220, 239, 227)
        Note over S,MG: Phase 2 · one MongoDB multi-document transaction
        S->>MG: startTransaction
        S->>MG: insert activity_logs {action: TRANSFER}
        S->>MG: insert 2 notifications (sender, receiver)
        S->>MG: delete transfer_drafts (if sent from a draft)
        S->>MG: commitTransaction (or abort as a whole)
        end
        V-->>C: redirect to receipt, "Transfer successful. Ref TXN…"
    end
```
