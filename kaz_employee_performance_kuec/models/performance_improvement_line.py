# -*- coding: utf-8 -*-
from odoo import fields, models


class PerformanceImprovementLine(models.Model):
    _name = 'performance.improvement.line'
    _description = 'Performance Improvement Line'
    _check_company_auto = True

    name = fields.Char(string='Goal')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    expected_standard = fields.Char(string='Expected Standard')
    evaluation_method = fields.Many2one('evaluation.method', string='Evaluation Method')
    due_date = fields.Date(string='Due Date')
    improvement_plan_id = fields.Many2one('performance.improvement.plan', string='Improvement Plan')
