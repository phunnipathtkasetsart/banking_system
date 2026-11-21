# NoSQL document schema (MongoDB)

Four collections. Ticket replies are embedded in `support_tickets.messages[]` (appended with `$push`). `userId` / `fromAccountId` point to SQL rows by convention; MongoDB does not enforce them.

| Collection | Indexes |
|---|---|
| activity_logs | `{userId: 1, timestamp: -1}`, `{action: 1}` |
| notifications | `{userId: 1, isRead: 1, sentAt: -1}` |
| support_tickets | `{userId: 1, status: 1}` |
| transfer_drafts | `{userId: 1, updatedAt: -1}` |

```mermaid
---
title: DigiBank NoSQL schema (MongoDB, database "digibank") · dotted lines = logical references to SQL, not enforced
---
erDiagram
    support_tickets ||--|{ ticket_message : "messages[] (embedded array)"
    users_user_sql ||..o{ activity_logs : "userId"
    users_user_sql ||..o{ notifications : "userId"
    users_user_sql ||..o{ support_tickets : "userId"
    users_user_sql ||..o{ transfer_drafts : "userId"
    banking_account_sql ||..o{ transfer_drafts : "fromAccountId"

    activity_logs {
        ObjectId _id PK
        int userId "null for a failed login"
        string username
        string action "LOGIN, TRANSFER, DEPOSIT, REVERSAL, ..."
        string status "SUCCESS | FAILED"
        string ip_address
        string user_agent
        object metadata "free-form, differs per action"
        bool reviewed "set by admin"
        string admin_note
        string reviewedBy "only after review"
        date reviewedAt "only after review"
        date timestamp
    }

    notifications {
        ObjectId _id PK
        int userId
        string title
        string message
        string category "INFO | TRANSACTION | SECURITY | BROADCAST | SUPPORT"
        bool isRead
        date sentAt
        date readAt "null until read"
    }

    support_tickets {
        ObjectId _id PK
        int userId
        string username
        string subject
        string category "ACCOUNT | TRANSFER | CARD | SECURITY | OTHER"
        string priority "LOW | MEDIUM | HIGH"
        string status "OPEN | IN_PROGRESS | RESOLVED | CLOSED"
        array messages "embedded, grows with $push"
        date createdAt
        date updatedAt
    }

    ticket_message {
        int authorId
        string authorName
        bool isStaff
        string body
        date createdAt
    }

    transfer_drafts {
        ObjectId _id PK
        int userId
        int fromAccountId
        string fromAccountNumber
        string toAccountNumber
        string amount "decimal kept as string, e.g. 88.00"
        string description
        date createdAt
        date updatedAt
    }

    users_user_sql["users_user (PostgreSQL)"] {
        bigint id PK
    }

    banking_account_sql["banking_account (PostgreSQL)"] {
        bigint id PK
    }
```
