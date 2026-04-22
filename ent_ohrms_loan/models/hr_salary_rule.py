# -*- coding: utf-8 -*-
from odoo import models, fields


class HrSalaryRule(models.Model):
    """Extends hr.salary.rule to support company-specific configurations."""
    _inherit = 'hr.salary.rule'

    company_id = fields.Many2one('res.company',
                                 'Company',
                                 copy=False,
                                 readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 help="Company this rule belongs to. Used in multi-company setup.")
