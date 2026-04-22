# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        """
        Override to apply parent restrictions ONLY to KUEC company.
        Non-KUEC records skip this check entirely.
        """
        # 1. Filter 'self' to find only records belonging to KUEC
        # (Assumes 'code' is a field you have on res.company)
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])

        # 2. If KUEC records exist in this batch, call the parent method ONLY for them.
        if kuec_records:
            super(AccountMove, kuec_records)._constrains_partner_id()
