# -*- coding: utf-8 -*-
from odoo import models, fields


class ISOCertification(models.Model):
    _name = 'iso.certification'
    _description = 'ISO Certification'
    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)