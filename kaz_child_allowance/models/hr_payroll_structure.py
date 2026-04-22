# -*- coding: utf-8 -*-
"""
Extends the HR Payroll Structure model to include a default salary rule
for 'Child Allowance' in the payroll computation.
"""

from odoo import models, api, fields, _


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        """
        Override the default salary rule generator to include a custom
        'Child Allowance' rule in newly created payroll structures.

        This method:
        - Calls the super method to retrieve existing default rules.
        - Appends a new rule that uses the `payslip.child_allowance_kaz` value.
          (This assumes a field or computed method with this name exists
          in the `hr.payslip` model.)

        Returns:
            list of (0, 0, dict) tuples defining salary rule records to create.
        """
        # Get existing default salary rules (from super)
        res = super()._get_default_rule_ids()

        # Append the custom 'Child Allowance' rule
        res.append((0, 0, {
            'name': _('Child Allowance'),            # Rule name (shown on payslip)
            'sequence': 197,                         # Determines order of computation
            'code': 'CHLALW',                        # Unique code used in reports/formulas
            'category_id': self.env.ref('hr_payroll.ALW').id,  # Belongs to the 'Allowance' category
            'condition_select': 'none',              # Always applied (no condition)
            'amount_select': 'code',                 # Amount is calculated via Python code
            'amount_python_compute': "result = payslip.child_allowance_kaz",  # Python logic
        }))

        return res

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Salary rules define components such as basic, allowances, deductions etc."
    )
