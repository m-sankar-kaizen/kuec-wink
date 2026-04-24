# -*- coding: utf-8 -*-
from odoo import models, api, fields, _, Command


class HrPayrollStructure(models.Model):
    """
    Extension of the hr.payroll.structure model to include default salary rules
    for child-related education allowances such as books, transportation, tuition,
    and other fees.

    These rules are automatically added to new payroll structures by default.
    """
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        """
        Returns a list of default salary rules related to child education allowances.

        This method extends the default salary rules provided by Odoo by adding
        four new rules:
        - Book Allowance
        - Transportation Allowance
        - Tuition Allowance
        - Other Fees Allowance

        Each rule uses Python code to compute the result from corresponding fields
        on the payslip (`payslip.book_fees`, `payslip.transportation_fees`, etc.).

        :return: A list of tuple commands to create default salary rules.
        :rtype: list
        """
        res = super()._get_default_rule_ids()
        res.extend([
            Command.create({
                'name': _('Child Book Allowance'),
                'sequence': 197,
                'code': 'CHILDALWBOOK',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.book_fees",
            }),
            Command.create({
                'name': _('Child Transportation Allowance'),
                'sequence': 198,
                'code': 'CHILDALWTRANSPORT',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.transportation_fees",
            }),
            Command.create({
                'name': _('Child Tuition Allowance'),
                'sequence': 199,
                'code': 'CHILDALWTUITION',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.tuition_fees",
            }),
            Command.create({
                'name': _('Child Other Fees Allowance'),
                'sequence': 200,
                'code': 'CHILDALWOTHERFEES',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.other_fees",
            }),
        ])
        return res

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Defines the salary rules applicable under this payroll structure, "
             "including child allowance components.")
