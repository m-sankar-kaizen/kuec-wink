# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RFQLineMixin(models.AbstractModel):
    _name = 'rfq.line.mixin'
    _description = 'RFQ Line Mixin'
    _check_company_auto = True

    product_id = fields.Many2one('product.product', string='Product')
    name = fields.Char(string='Name', related='product_id.name')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', string='Account')
    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        help="Distribution of the line amount across analytic accounts in percentage."
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get("Percentage Analytic"),
        help="Decimal precision used to round analytic percentages."
    )
    qty = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Price Unit')
    amount_in_currency = fields.Float(
        string='Total Amount in Currency',
        compute='_compute_amount_in_currency',
        store=True,
        help="Total line amount in the selected currency."
    )
    uom_id = fields.Many2one('uom.uom', string='UoM', help="Unit of Measure of the product.",
                             compute='_compute_uom_id', store=True)

    @api.depends('product_id')
    def _compute_uom_id(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_po_id.id if rec.product_id else False

    def _compute_amount_in_currency(self):
        for rec in self:
            rec.amount_in_currency = 0
