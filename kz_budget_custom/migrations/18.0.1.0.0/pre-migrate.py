# -*- coding: utf-8 -*-
from openupgradelib import openupgrade
from odoo.tools import SQL


def migrate(cr, version):
    if not version:
        return

    # Add missing column general_budget_id
    if not openupgrade.column_exists(cr, "budget_line", "general_budget_id"):
        openupgrade.logged_query(
            cr,
            "ALTER TABLE budget_line ADD COLUMN general_budget_id INTEGER"
        )

    # Ensure account_budget_post table exists
    if not openupgrade.table_exists(cr, "account_budget_post"):
        cr.execute("""
            CREATE TABLE account_budget_post (
                id SERIAL PRIMARY KEY,
                name VARCHAR,
                company_id INTEGER,
                create_uid INTEGER,
                create_date TIMESTAMP,
                write_uid INTEGER,
                write_date TIMESTAMP
            )
        """)
        cr.execute("""
            CREATE TABLE account_budget_rel (
                budget_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL
            )
        """)
        # STEP 3: Update hr_department.budget_id to new budget_analytic ids
        table_column_map = {
            "hr_department": ["budget_id"],
        }

        for table, columns in table_column_map.items():
            for column in columns:
                if openupgrade.column_exists(cr, table, column):
                    if openupgrade.table_exists(cr, "crossovered_budget"):
                        cr.execute(
                            SQL(
                                """
                                UPDATE %(table)s d
                                SET %(column)s = b_new.id
                                FROM budget_analytic b_new
                                JOIN crossovered_budget b_old ON b_old.name = b_new.name
                                WHERE d.%(column)s = b_old.id
                                """,
                                table=SQL.identifier(table),
                                column=SQL.identifier(column),
                            )
                        )

    # Map old general_budget_id → new budget_id
    if openupgrade.table_exists(cr, "crossovered_budget_lines") and openupgrade.table_exists(
            cr, "budget_line"):
        cr.execute(
            SQL(
                """
                UPDATE budget_line bl
                SET budget_id = b_new.id
                FROM crossovered_budget_lines cbl
                JOIN crossovered_budget cb_old ON cbl.general_budget_id = cb_old.id
                JOIN budget b_new ON b_new.name = cb_old.name
                WHERE bl.id = cbl.id
                """,
                table=SQL.identifier("budget_line"),
            )
        )
