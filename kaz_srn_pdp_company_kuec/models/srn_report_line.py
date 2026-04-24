# -*- coding: utf-8 -*-
from odoo import models, fields


class SRNReportLine(models.Model):
    _name = 'srn.report.line'
    _description = 'SRN Report Line'
    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    company_code = fields.Selection(related='company_id.company_code')
    sequence = fields.Integer('Sequence')
    srn_report_template_line_id = fields.Many2one('srn.report.template.line',
                                                  'SRN Report Template Line')
    available_answer_selection_ids = fields.Many2many(related='srn_report_template_line_id.answer_selection_ids')
    answer_selection_id = fields.Many2one('answer.selection', string='Answers')
    remarks = fields.Char('Remarks')
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order')
