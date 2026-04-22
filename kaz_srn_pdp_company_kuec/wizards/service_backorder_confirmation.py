# -*- coding: utf-8 -*-
from odoo import fields, models


class ServiceBackorderConfirmation(models.TransientModel):
    _inherit = 'service.backorder.confirmation'

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    company_code = fields.Selection(string='Company Code', related='company_id.company_code')
