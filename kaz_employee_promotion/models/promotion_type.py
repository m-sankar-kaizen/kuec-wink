# -*- coding: utf-8 -*-
from odoo import fields, models


class PromotionType(models.Model):
    """This model is used for the Promotion Type of Employee"""
    _name = 'promotion.type'
    _description = 'Promotion Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Promotion Type', help='Promotion type', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
