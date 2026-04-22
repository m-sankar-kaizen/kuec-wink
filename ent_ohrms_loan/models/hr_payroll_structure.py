# -*- coding: utf-8 -*-
"""
Models Extended:
----------------
- hr.salary.rule
- hr.payroll.structure
"""

from odoo import models, fields


class HrPayrollStructure(models.Model):
    """Extends hr.payroll.structure to
    support company-specific configurations."""
    _inherit = 'hr.payroll.structure'

    company_id = fields.Many2one('res.company', 'Company',
                                 copy=False,
                                 readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 help="Company this structure belongs to. "
                                      "Used in multi-company setup.")
