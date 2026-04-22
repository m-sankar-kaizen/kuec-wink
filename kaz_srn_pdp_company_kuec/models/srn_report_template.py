# -*- coding: utf-8 -*-
from odoo import models, fields


class SRNReportTemplate(models.Model):
    _name = 'srn.report.template'
    _description = 'SRN Report Template'
    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    company_code = fields.Selection(related='company_id.company_code')
    srn_report_template_line_ids = fields.One2many('srn.report.template.line',
                                                   'srn_report_template_id',
                                                   string='SRN Report Template Lines')
