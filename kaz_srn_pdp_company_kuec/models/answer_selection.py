# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AnswerSelection(models.Model):
    _name = 'answer.selection'
    _description = 'Answer Selection'
    _check_company_auto = True

    name = fields.Char(string='Answer Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    company_code = fields.Selection(related='company_id.company_code')
