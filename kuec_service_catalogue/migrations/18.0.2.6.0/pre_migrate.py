# -*- coding: utf-8 -*-
"""
Migration 18.0.2.6.0 — add missing res_company columns.

wink_terms_html was added to res_company in Python but the DB column
was never created on Odoo.sh (module was never upgraded after the field
was introduced). Adding it here so the upgrade completes cleanly.
"""


def migrate(cr, version):
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS wink_terms_html text;
    """)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS wink_reminder_days_before varchar;
    """)
