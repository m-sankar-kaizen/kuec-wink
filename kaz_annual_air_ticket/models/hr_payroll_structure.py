# -*- coding: utf-8 -*-
from odoo import models, api, fields, _, Command


class HrPayrollStructure(models.Model):
    """
    Inherits `hr.payroll.structure` to inject default salary rules
    for Leave Travel Allowance (LTA) and Housing Advance components.

    This extension dynamically adds:
    - A rule for Leave Travel Allowance based on total ticket price
    - A rule for Housing Advance Deduction
    - A rule for Housing Advance Grant

    These rules can be applied to payslips for automatic computation
    based on respective custom methods defined in `hr.payslip`.
    """
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        """
        Override default salary rules to include:
        - Leave Travel Allowance (LTA)
        - Housing Advance Deduction
        - Housing Advance Grant

        These rules use custom computation via Python code expressions.
        """
        res = super()._get_default_rule_ids()
        res.extend([
            # Rule for Leave Travel Allowance (LTA)
            Command.create({
                'name': _('Leave Travel Allowance'),
                'sequence': 197,
                'code': 'LVETRAALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.ticket_total_price",
            }),
            # Rule for Housing Advance Deduction
            Command.create({
                'name': _('Housing Advance Deduction'),
                'sequence': 198,
                'code': 'HOADLWD',
                'category_id': self.env.ref('hr_payroll.DED').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.housing_advance_deduction",
            }),
            # Rule for Housing Advance Grant (Allowance)
            Command.create({
                'name': _('Housing Advance Amount'),
                'sequence': 197,
                'code': 'HOADALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.housing_advance_grant",
            }),
        ])
        return res

    rule_ids = fields.One2many(
        'hr.salary.rule',
        'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Salary rules attached to this structure. Includes LTA and Housing Advance rules."
    )
