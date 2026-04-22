from odoo import models, api, fields, _


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        res = super()._get_default_rule_ids()

        res.append((0, 0, {
            'name': _('Disciplinary Deduction'),
            'sequence': 197,
            'code': 'DISDED',
            'category_id': self.env.ref('hr_payroll.DED').id,
            'condition_select': 'none',
            'amount_select': 'code',
            'amount_python_compute': "result = payslip.disciplinary_deduction_amt"
        }))

        return res

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Salary rules define components "
             "such as basic, allowances, deductions etc."
    )
