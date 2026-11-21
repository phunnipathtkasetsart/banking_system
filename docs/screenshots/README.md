# Screenshots

21 features, in three folders. Each folder has its own `SHOTLIST.md` with filenames, steps and what each image must show.

1. [01-sql-postgresql/](01-sql-postgresql/SHOTLIST.md): SQL features, shots 01–12
2. [02-nosql-mongodb/](02-nosql-mongodb/SHOTLIST.md): NoSQL features, shots 13–17
3. [03-transaction-proof/](03-transaction-proof/SHOTLIST.md): successful transfer, rollback, rejections and the CHECK constraint, shots 18–21

Do the folders in this order; later shots rely on data created by earlier ones.

## Before you start

1. Reset to clean demo data so the numbers match across every screenshot:
   ```bash
   docker compose down -v
   docker compose up -d --build
   docker compose exec web python manage.py seed_demo
   ```
2. Browser window about 1440 × 900, zoom 100%.
3. Logins: `admin / Admin@12345`, `alice / Customer@123`, `bob / Customer@123`.
4. Capture the green or red message bar whenever a step changes data.
