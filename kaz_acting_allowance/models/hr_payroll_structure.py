# -*- coding: utf-8 -*-
from odoo import models, api, fields, _, Command


class HrPayrollStructure(models.Model):
    """
    Extend Payroll Structure to add default salary rules for Acting Allowance.

    This module adds two salary rules:
    1. Acting Allowance (ACTALW): Computed from the employee's contract field `acting_allowance_amount`.
    2. Acting Allowance Leave Deduction (ACTLWD): Deduction rule computed using a method defined on hr.payslip.
    """
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        """
        Adds default salary rules for acting allowance and leave deduction.

        :return: A list of rule tuples to be appended to the payroll structure.
        """
        res = super()._get_default_rule_ids()
        res.extend([
            Command.create({
                'name': _('Acting Allowance'),
                'sequence': 197,
                'code': 'ACTALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.acting_allowance_amount",
            }),
            Command.create({
                'name': _('Acting Allowance Leave Deduction'),
                'sequence': 198,
                'code': 'ACTLWD',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': (
                    "result = payslip.env['hr.payslip']"
                    ".acting_allowance_deduction()"
                ),
            }),
        ])
        return res

    rule_ids = fields.One2many(
        'hr.salary.rule',
        'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Defines the salary rules that are part of this structure, "
             "including acting allowance and any deductions related to it."
    )
