# -*- coding: utf-8 -*-
from openupgradelib import openupgrade
from odoo.tools import SQL


def migrate(cr, version):
    if not version:
        return

    # Check if both custom columns exist before proceeding
    if (
            openupgrade.column_exists(cr, "account_move", "manual_currency_rate_active")
            and openupgrade.column_exists(cr, "account_move", "manual_currency_rate")
    ):
        # Update only where manual rate was active
        cr.execute(SQL("""
            UPDATE account_move
            SET invoice_currency_rate = manual_currency_rate
            WHERE manual_currency_rate_active = TRUE
              AND manual_currency_rate IS NOT NULL
        """))