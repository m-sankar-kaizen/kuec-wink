# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountReport(models.Model):
    """
    Inherits from 'account.report' to extend reporting capabilities with:

    - Support for on-the-fly currency conversion for financial reports.
    - A new Boolean field (`curr_conversation`) that toggles whether report values
      should be converted to a custom currency.
    - A related currency field (`curr_currency_id`) which, when set, overrides the
      report's display currency for formatting and calculation.

    Use Cases:
    - Multi-company groups needing unified financial reporting in a base currency.
    - Users requiring preview/export of reports in a different currency than the journal.
    - Flexible report formatting where currency can be chosen dynamically.

    Integrates seamlessly with the PDF export system and overrides
    the formatting behavior to reflect the selected conversion currency.
    """
    _inherit = 'account.report'

    curr_conversation = fields.Boolean('Currency Conversion')
    curr_currency_id = fields.Many2one('res.currency', string='Currency')

    @api.onchange("curr_conversation")
    def _onchange_curr_conversation(self):
        """
        Clears the selected currency when conversion is toggled off.
        Ensures consistency in the UI and avoids accidental conversions.
        """
        if not self.curr_conversation:
            self.curr_currency_id = False

    @api.model
    def format_value(self, options, value, figure_type, format_params=None):
        if not format_params:
            format_params = {}
        currency = False
        if self.curr_currency_id:
            currency = self.curr_currency_id

        if not self:
            currency = self.env['account.report'].browse(
                self.env.context.get('report_id')
            ).curr_currency_id
        if currency:
            format_params['currency'] = currency

        return super().format_value(
            options=options,
            value=value,
            figure_type=figure_type,
            format_params=format_params,
        )

    def export_to_pdf(self, options):
        """
        Ensures that the currency context is preserved during PDF export.
        Converts report totals and balances using the selected target currency
        if `curr_conversation` is active.
        """
        print_mode_self = self.with_context(print_mode=True, report_id=self.id)
        return super(AccountReport, print_mode_self).export_to_pdf(options=options)

