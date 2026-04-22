# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    """
    Inherits the 'account.move' model to introduce support for
    manual currency exchange rates on accounting entries, particularly
    for invoices and bills. This allows overriding the standard
    currency conversion mechanism.
    """
    _inherit = 'account.move'

    # Boolean field to activate manual exchange rate usage
    manual_currency_rate_active = fields.Boolean('Apply Manual Exchange')

    # Float field to manually set the currency rate
    manual_currency_rate = fields.Float('Rate', digits=(12, 10))

    invoice_currency_rate = fields.Float(
        string='Currency Rate',
        compute='_compute_currency_rate', store=True, precompute=True,
        readonly=False,
        copy=False,
        digits=0,
        help="Currency rate from company currency to document currency.",
    )

    @api.depends('currency_id', 'company_currency_id', 'company_id')
    def _compute_currency_rate(self):
        for move in self:
            if move.is_invoice(include_receipts=True):
                move.invoice_currency_rate = move.expected_currency_rate
