# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    srn_report_template_id = fields.Many2one('srn.report.template', 'SRN Report Template')
