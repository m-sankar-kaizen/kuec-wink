# -*- coding: utf-8 -*-
from odoo import models, api, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    company_code = fields.Selection(related="company_id.company_code", string="Company Code")

    @api.constrains('partner_id')
    def _constrains_partner_id(self):
        kuec_records = self.filtered(lambda rec: rec.company_code in ['KUEC'])
        if kuec_records:
            super(SaleOrder, kuec_records)._constrains_partner_id()

    def _validate_partner_state(self):
        self.ensure_one()
        if self.company_code in ['KUEC']:
            super()._validate_partner_state()
