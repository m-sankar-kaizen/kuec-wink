# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EvaluationMethod(models.Model):
    _name = 'evaluation.method'
    _description = 'Evaluation Method'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
