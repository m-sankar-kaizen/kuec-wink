# -*- coding: utf-8 -*-

from odoo import models, fields


class WinkRetainerPlan(models.Model):
    _name = 'wink.retainer.plan'
    _description = 'WINK Retainer Plan'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Retainer Service',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(
        string='Plan Name',
        required=True,
        help='e.g. Basic (10h/mo), Professional (20h/mo), Enterprise (40h/mo)',
    )
    sequence = fields.Integer(default=10)
    price = fields.Float(
        string='Price',
        required=True,
        digits=(10, 2),
    )
    description = fields.Text(string='Description')
