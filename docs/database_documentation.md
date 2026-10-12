# Database Documentation

This folder contains database-level documentation generated from the PostgreSQL schema.

## Physical table names (`DB_TABLE_PREFIX`)

Application tables use the prefix configured in `DB_TABLE_PREFIX` (default **`dsg_hr_`**).

Examples:

| Logical (Django default) | PostgreSQL |
|--------------------------|------------|
| `base_company` | `dsg_hr_base_company` |
| `horilla_auth_horillauser` | `dsg_hr_horilla_auth_horillauser` |
| `django_migrations` | `django_migrations` (no prefix) |

Full rules, backups, and DBA SQL notes: **[database_table_prefix.md](./database_table_prefix.md)**.

Regenerate the CSV files below from a migrated database:

```bash
python manage.py export_db_schema_docs
# Docker:
docker compose exec web python manage.py export_db_schema_docs
```

## Files

- `db_table_documentation.csv`
  - Full table-level documentation.
  - Includes actual table name, simple name, table purpose, and columns.

- `db_modules_summary.csv`
  - Module-wise summary.
  - Shows how many tables and columns belong to each app/module prefix.

- `../db_schema_columns.csv` (repository root)
  - Column-level export for spreadsheets and data dictionaries.

## Main Columns

`db_table_documentation.csv` uses this structure:

| Column | Meaning |
| --- | --- |
| `table_name` | Actual PostgreSQL table name used by the project. |
| `simple_table_name` | Human-friendly table name. |
| `work_of_the_table` | Short explanation of what kind of data the table stores. |
| `columns` | Column list with type, primary key, foreign key, and nullable/required information. |

## Notes

- Tables like `auth_*`, `django_*`, `token_blacklist_*`, and `axes_*` are framework/security tables.
- Tables with three columns and two foreign keys are usually many-to-many relationship tables.
- Tables containing `historical` are audit/history tables.
- Tables ending with relation-style names like `_company_id`, `_attachments`, `_files`, or `_images` are usually join/link tables.

The `work_of_the_table` column is generated from table naming patterns and foreign keys, so it is meant as a practical understanding aid rather than official business wording.
