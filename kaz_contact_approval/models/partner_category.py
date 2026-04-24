# -*- coding: utf-8 -*-
from odoo import models, fields


class PartnerCategory(models.Model):
    _name = 'partner.category'
    _description = 'Partner Category'
    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )