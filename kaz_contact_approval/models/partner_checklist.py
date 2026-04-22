# -*- coding: utf-8 -*-
from odoo import fields, models


class PartnerChecklist(models.Model):
    _name = 'partner.checklist'
    _description = 'Partner Checklist'
    _check_company_auto = True

    name = fields.Char('Question Name', required=True)
    sequence = fields.Integer('Sequence')
    is_checked = fields.Boolean('Checked')
    for_customer = fields.Boolean('For Customer')
    for_vendor = fields.Boolean('For Vendor')
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
