# Database table prefix (`DB_TABLE_PREFIX`)

DSG HRMS uses a configurable **physical table name prefix** on PostgreSQL/SQLite application tables. The default is `dsg_hr_`.

## Naming rules

| Item | Example |
|------|---------|
| Setting | `DB_TABLE_PREFIX=dsg_hr_` |
| Django app label + model | `base` + `Company` |
| Default (unprefixed) name | `base_company` |
| **Physical table in PostgreSQL** | `dsg_hr_base_company` |

**Not prefixed** (unchanged Django/vendor names):

- `django_*` — migrations, sessions, content types, etc.
- `auth_*` — Django auth tables (`auth_permission`, `auth_group`, …)
- `auditlog_*`, `axes_*`, `notifications_*`, `token_blacklist_*`, `django_apscheduler_*`
- Models with an explicit `Meta.db_table` on the model class (e.g. `LegacyUser` → `auth_user`, `managed=False`)

Custom user data lives in **`dsg_hr_horilla_auth_horillauser`** (not `auth_user`).

## Configuration

| Location | Variable |
|----------|----------|
| `.env` / `.env.dist` | `DB_TABLE_PREFIX=dsg_hr_` |
| `docker-compose.yml` | `DB_TABLE_PREFIX=dsg_hr_` on `web` and `scheduler` |
| `horilla/settings/base.py` | `DB_TABLE_PREFIX` (default `dsg_hr_`) |

Set `DB_TABLE_PREFIX=` (empty) only for legacy databases that were **never** migrated to prefixed names. The value must match what was used when migrations were applied.

## Migrations

Table renames are applied by auto-generated migrations (`AlterModelTable`), for example:

- `base/migrations/0017_alter_announcement_table_and_more.py`
- `horilla_auth/migrations/0002_alter_horillauser_table.py`

On a **new** database, `migrate` runs the full chain; the final schema uses prefixed names.

## Backups and restore

`pg_dump` / `pg_restore` capture **actual** table names. No special flags are required.

```bash
# Backup (same as before — database name is still horilla_db by default)
docker compose exec db pg_dump -U horilla_user horilla_db > backup.sql

# Restore
cat backup.sql | docker compose exec -T db psql -U horilla_user -d horilla_db
```

After restore, run the application with the **same** `DB_TABLE_PREFIX` that was used when the dump was taken.

Horilla in-app backup (Google Drive / local) uses Django/database dumps at the database level; prefixed tables are included automatically.

## DBA / BI / raw SQL

- Prefer Django ORM or `Model._meta.db_table` in application code.
- Ad-hoc SQL must use prefixed names, e.g. `SELECT * FROM dsg_hr_base_company`.
- List application tables:

```sql
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE 'dsg_hr_%'
ORDER BY 1;
```

## Schema documentation CSV files

Regenerate from a migrated database (PostgreSQL):

```bash
docker compose exec web python manage.py export_db_schema_docs
```

Updates:

- `docs/db_table_documentation.csv`
- `docs/db_modules_summary.csv`
- `db_schema_columns.csv` (repository root)

Commit the CSVs after major schema or prefix changes so DBAs and reports stay aligned.
