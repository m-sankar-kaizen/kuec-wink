# -*- coding: utf-8 -*-
from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # @api.constrains('partner_id')
    # def _constrains_partner_id(self):
    #     """
    #     Override to apply parent restrictions ONLY to KUEC/WINK company.
    #     Non-KUEC/WINK records skip this check entirely.
    #     """
    #     applicable_records = self.filtered(lambda rec: rec.company_code in ['KUEC', 'WINK'])
    #     if applicable_records:
    #         super(AccountMoveLine, applicable_records)._constrains_partner_id()
