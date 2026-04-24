# -*- coding: utf-8 -*-
from odoo import models, api, fields


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])
        if kuec_records:
            super(AccountPayment, kuec_records)._constrains_partner_id()
