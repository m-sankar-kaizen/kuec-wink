# -*- coding: utf-8 -*-
from odoo import models, api, fields, _, Command


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        res = super()._get_default_rule_ids()
        res.extend([
            Command.create({
                'name': _('Secondment Allowance'),
                'sequence': 76,
                'code': 'SECONDMENTALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = payslip.secondment_amount",
            }),
        ])
        return res

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Defines the salary rules applicable under this payroll structure, "
             "including child allowance components.")
