# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    ceo_job_id = fields.Many2one('hr.job', string='Ceo Job')
