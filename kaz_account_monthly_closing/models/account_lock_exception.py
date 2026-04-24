# -*- coding: utf-8 -*-
from odoo import fields, models

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS


class AccountLockException(models.Model):
    _inherit = "account.lock_exception"

    br_gl_lock_date = fields.Date(
        string='Full Ledger Lock Date',
        compute="_compute_lock_dates",
        search="_search_br_gl_lock_date",
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )

    # The changed lock date
    lock_date_field = fields.Selection(
        selection_add=[
            ('br_gl_lock_date', 'Full Ledger Lock Date')
        ],
        ondelete={'br_gl_lock_date': 'cascade'}
    )

    def _search_br_gl_lock_date(self, operator, value):
        return self._search_lock_date('br_gl_lock_date', operator, value)
