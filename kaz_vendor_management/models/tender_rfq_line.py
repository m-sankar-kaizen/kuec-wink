# -*- coding: utf-8 -*-
from odoo import models, fields, api


class TenderRFQLine(models.Model):
    _name = 'tender.rfq.line'
    _description = 'Tender RFQ Line'
    _inherit = 'rfq.line.mixin'

    currency_id = fields.Many2one(related='tender_rfq_id.currency_id', string='Currency')
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ')

    @api.depends('product_id', 'qty', 'price_unit', 'currency_id',
                 'tender_rfq_id.manual_currency_rate')
    def _compute_amount_in_currency(self):
        """
        Compute line amount based on whether the line currency differs from company currency.
        Applies manual currency rate if needed.
        """
        for line in self:
            amount = 0
            if self.currency_id:
                if self.currency_id.id == self.env.company.currency_id.id:
                    amount += line.qty * line.price_unit
                else:
                    amount += line.qty * line.price_unit * line.tender_rfq_id.manual_currency_rate
            line.amount_in_currency = amount
