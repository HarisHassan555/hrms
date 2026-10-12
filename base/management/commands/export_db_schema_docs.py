"""
Export PostgreSQL schema metadata to CSV files for DBA documentation.

Requires a migrated database (with the current DB_TABLE_PREFIX applied).
"""

import csv
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = (
        "Write docs/db_table_documentation.csv, docs/db_modules_summary.csv, "
        "and db_schema_columns.csv from the live database schema."
    )

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError(
                "export_db_schema_docs requires PostgreSQL (current: "
                f"{connection.vendor})."
            )

        base_dir = Path(settings.BASE_DIR)
        docs_dir = base_dir / "docs"
        docs_dir.mkdir(exist_ok=True)

        prefix = (getattr(settings, "DB_TABLE_PREFIX", None) or "").strip()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.table_name, c.column_name, c.ordinal_position,
                       c.data_type, c.udt_name, c.is_nullable, c.column_default,
                       c.character_maximum_length, c.numeric_precision,
                       c.numeric_scale
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_schema = c.table_schema
                 AND t.table_name = c.table_name
                WHERE c.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
                ORDER BY c.table_name, c.ordinal_position
                """
            )
            column_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT kcu.table_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 'public'
                  AND tc.constraint_type = 'PRIMARY KEY'
                """
            )
            pk_cols = {(r[0], r[1]) for r in cursor.fetchall()}

            cursor.execute(
                """
                SELECT kcu.table_name, kcu.column_name,
                       ccu.table_name, ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                 AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                 AND ccu.table_schema = tc.table_schema
                WHERE tc.table_schema = 'public'
                  AND tc.constraint_type = 'FOREIGN KEY'
                """
            )
            fk_map = {
                (r[0], r[1]): (r[2], r[3]) for r in cursor.fetchall()
            }

        schema_path = base_dir / "db_schema_columns.csv"
        with schema_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "table_name",
                    "ordinal_position",
                    "column_name",
                    "data_type",
                    "udt_name",
                    "is_nullable",
                    "column_default",
                    "character_maximum_length",
                    "numeric_precision",
                    "numeric_scale",
                    "is_primary_key",
                    "foreign_table_name",
                    "foreign_column_name",
                ]
            )
            for row in column_rows:
                table_name, col_name = row[0], row[1]
                fk = fk_map.get((table_name, col_name), ("", ""))
                writer.writerow(
                    [
                        table_name,
                        row[2],
                        col_name,
                        row[3],
                        row[4],
                        row[5],
                        row[6] or "",
                        row[7] or "",
                        row[8] or "",
                        row[9] or "",
                        "YES" if (table_name, col_name) in pk_cols else "NO",
                        fk[0],
                        fk[1],
                    ]
                )

        tables: dict[str, list] = defaultdict(list)
        for row in column_rows:
            tables[row[0]].append(row)

        table_doc_path = docs_dir / "db_table_documentation.csv"
        with table_doc_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "table_name",
                    "simple_table_name",
                    "work_of_the_table",
                    "columns",
                ]
            )
            for table_name in sorted(tables):
                simple = self._simple_name(table_name, prefix)
                purpose = self._table_purpose(table_name, prefix)
                col_parts = []
                for row in tables[table_name]:
                    col_name = row[1]
                    nullable = row[5] == "YES"
                    req = "nullable" if nullable else "required"
                    pk = "PK, " if (table_name, col_name) in pk_cols else ""
                    fk = fk_map.get((table_name, col_name))
                    fk_part = (
                        f"FK -> {fk[0]}.{fk[1]}, " if fk and fk[0] else ""
                    )
                    col_parts.append(
                        f"{col_name} ({row[3]}, {pk}{fk_part}{req})".replace(
                            ", )", ")"
                        )
                    )
                writer.writerow(
                    [table_name, simple, purpose, "; ".join(col_parts)]
                )

        module_tables: dict[str, list[str]] = defaultdict(list)
        module_cols: dict[str, int] = defaultdict(int)
        for table_name, cols in tables.items():
            module = self._module_name(table_name, prefix)
            module_tables[module].append(table_name)
            module_cols[module] += len(cols)

        summary_path = docs_dir / "db_modules_summary.csv"
        with summary_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                ["module_name", "table_count", "column_count", "tables"]
            )
            for module in sorted(module_tables):
                names = sorted(module_tables[module])
                writer.writerow(
                    [
                        module,
                        len(names),
                        module_cols[module],
                        ", ".join(names),
                    ]
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {len(tables)} tables "
                f"(DB_TABLE_PREFIX={prefix or '(none)'}) to docs/ and db_schema_columns.csv"
            )
        )

    @staticmethod
    def _strip_prefix(table_name: str, prefix: str) -> str:
        if prefix and table_name.startswith(prefix):
            return table_name[len(prefix) :]
        return table_name

    def _module_name(self, table_name: str, prefix: str) -> str:
        logical = self._strip_prefix(table_name, prefix)
        if logical.startswith("django_"):
            return "django"
        if logical.startswith("auth_"):
            return "auth"
        if logical.startswith("auditlog_"):
            return "auditlog"
        if logical.startswith("axes_"):
            return "axes"
        if logical.startswith("token_blacklist_"):
            return "token_blacklist"
        if logical.startswith("notifications_"):
            return "notifications"
        return logical.split("_", 1)[0] if "_" in logical else logical

    def _simple_name(self, table_name: str, prefix: str) -> str:
        logical = self._strip_prefix(table_name, prefix)
        parts = logical.split("_")
        if len(parts) > 1:
            return parts[-1].replace("_", " ").title()
        return logical.title()

    def _table_purpose(self, table_name: str, prefix: str) -> str:
        logical = self._strip_prefix(table_name, prefix)
        if logical.count("_") >= 2 and logical.endswith(
            ("_employees", "_company_id", "_attachments", "_files", "_images")
        ):
            return (
                "Relationship/junction table linking related records "
                "(many-to-many or attachments)."
            )
        if "historical" in logical:
            return f"Audit/history table for the {logical.split('_')[0]} module."
        module = self._module_name(table_name, prefix)
        return f"Stores data for the {module} module (table {logical})."
