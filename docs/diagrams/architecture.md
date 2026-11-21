# System architecture

Browser → Django (one container) → PostgreSQL and MongoDB (one container each), all on the Docker Compose network. No external APIs, CDNs or cloud databases: fonts, CSS and uploaded avatars are served from the app itself.

```mermaid
---
title: DigiBank system architecture (everything runs locally in Docker Compose)
---
flowchart LR
    subgraph client["Web browser"]
        UI["Server-rendered HTML pages<br/>CSS, fonts and images served by the app<br/>(no CDN)"]
    end

    subgraph compose["Docker Compose network · localhost"]
        direction LR
        subgraph web["web container · Django 5.2 · port 8000"]
            direction TB
            ROUTER["URL router<br/>config/urls.py"]
            APPS["Django apps<br/>users · banking · adminpanel<br/>activity · notifications · support"]
            ENGINE["Transaction engine<br/>banking/services.py"]
            ORM["Django ORM<br/>psycopg 3"]
            PYMONGO["Mongo access layer<br/>core/mongo.py · PyMongo"]
            ROUTER --> APPS
            APPS --> ENGINE
            APPS --> ORM
            APPS --> PYMONGO
            ENGINE -->|"phase 1: SQL transaction"| ORM
            ENGINE -->|"phase 2: Mongo transaction"| PYMONGO
        end

        PG[("PostgreSQL 16<br/>container: db<br/>5 tables<br/>money · accounts · ledger")]
        MONGO[("MongoDB 7 · replica set rs0<br/>container: mongo<br/>4 collections<br/>logs · notifications · tickets · drafts")]
        MEDIA[["media/ folder<br/>uploaded avatars<br/>on the server's disk"]]
    end

    UI <-->|"HTTP :8000<br/>session cookie + CSRF"| ROUTER
    ORM <-->|"SQL · ACID<br/>SELECT … FOR UPDATE"| PG
    PYMONGO <-->|"BSON · multi-document<br/>transactions"| MONGO
    APPS -->|"save / serve files"| MEDIA

    classDef sql fill:#dbe7f3,stroke:#336791,color:#17201c
    classDef nosql fill:#dcefe3,stroke:#13aa52,color:#17201c
    classDef app fill:#fafbf8,stroke:#4f5b55,color:#17201c
    class PG sql
    class MONGO nosql
    class ROUTER,APPS,ENGINE,ORM,PYMONGO,UI,MEDIA app
```
