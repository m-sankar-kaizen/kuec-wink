# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ServiceReceiptLine(models.Model):
    _inherit = 'service.receipt.line'

    price_unit = fields.Float(string='Unit Price')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)

    @api.depends('quantity_done', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.update({
                'price_subtotal': line.quantity_done * line.price_unit,
            })



