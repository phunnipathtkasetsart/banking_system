# SQL ER diagram (PostgreSQL)

Five tables. `banking_transactionentry` is the double-entry ledger: a transfer writes one DEBIT and one CREDIT line. `PROTECT` on entries → accounts stops a user or account with history from being deleted. Constraint names: `account_balance_non_negative`, `transaction_amount_positive`, `unique_beneficiary_per_user`.

```mermaid
---
title: DigiBank SQL schema (PostgreSQL) · ER diagram
---
erDiagram
    users_user ||--o{ banking_account : "owns"
    users_user ||--o{ banking_beneficiary : "saves payee"
    banking_account ||--o{ banking_beneficiary : "is saved as"
    banking_transaction ||--|{ banking_transactionentry : "has ledger lines"
    banking_account ||--o{ banking_transactionentry : "is posted to (PROTECT)"
    users_user |o--o{ banking_transaction : "created_by (SET NULL)"
    banking_transaction |o--o| banking_transaction : "reversal_of"

    users_user {
        bigint id PK
        varchar username UK
        varchar email UK
        varchar password "salted PBKDF2-SHA256 hash"
        varchar role "CUSTOMER | ADMIN"
        varchar first_name
        varchar last_name
        varchar phone
        varchar avatar "path under media/avatars/"
        boolean is_active
        boolean is_staff
        boolean is_superuser
        timestamptz date_joined
        timestamptz last_login
    }

    banking_account {
        bigint id PK
        bigint user_id FK "→ users_user.id (CASCADE)"
        varchar account_number UK "10 digits, shown as XXX-X-XXXXX-X"
        varchar account_type "SAVINGS | CHECKING | FIXED"
        varchar nickname
        numeric balance "(14,2) CHECK balance >= 0"
        varchar status "ACTIVE | FROZEN | CLOSED"
        timestamptz created_at
        timestamptz updated_at
    }

    banking_transaction {
        bigint id PK
        varchar reference UK "TXNyymmddXXXXXXXX"
        varchar txn_type "DEPOSIT | WITHDRAWAL | TRANSFER | REVERSAL"
        numeric amount "(14,2) CHECK amount > 0"
        varchar status "COMPLETED | REVERSED"
        varchar description
        bigint created_by_id FK "→ users_user.id, nullable"
        bigint reversal_of_id FK,UK "→ banking_transaction.id, nullable"
        timestamptz created_at
    }

    banking_transactionentry {
        bigint id PK
        bigint transaction_id FK "→ banking_transaction.id (CASCADE)"
        bigint account_id FK "→ banking_account.id (PROTECT)"
        varchar direction "DEBIT | CREDIT"
        numeric amount "(14,2)"
        numeric balance_after "(14,2) running balance"
        timestamptz created_at
    }

    banking_beneficiary {
        bigint id PK
        bigint user_id FK "→ users_user.id (CASCADE)"
        bigint account_id FK "→ banking_account.id (CASCADE)"
        varchar nickname
        timestamptz created_at
    }
```
