# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        """
        Override to apply parent restrictions ONLY to KUEC company.
        Non-KUEC records skip this check entirely.
        """
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])
        if kuec_records:
            super(AccountMoveLine, kuec_records)._constrains_partner_id()
