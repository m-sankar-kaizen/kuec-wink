# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrPayrollStructure(models.Model):
    """
    Inherits the `hr.payroll.structure` model to customize the default salary rules
    with institution-specific allowances and benefits.
    """
    _inherit = 'hr.payroll.structure'

    @api.model
    def _get_default_rule_ids(self):
        """
        Generate and return a list of default salary rules to be included in
        the payroll structure. This method adds custom rules like:
            - Living Allowance
            - Connectivity Allowance
            - Scale Basic Salary
            - Personal Allowance
            - Premium Allowance
            - Relocation Benefit
            - Repatriation Benefit
            - Educational Benefit

        Returns:
            list: A list of tuple-based rule definitions to be injected in payroll structure.
        """
        # Call super to fetch any pre-defined rules
        res = super()._get_default_rule_ids()

        # Extend with institution-specific rules
        res.extend([
            (0, 0, {
                'name': _('Living Allowance'),
                'sequence': 198,
                'code': 'LIVALL',
                'appears_on_employee_cost_dashboard': True,
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = contract.living_allowance + contract.living_allowance_additional',
            }),
            (0, 0, {
                'name': _('Connectivity Allowance'),
                'sequence': 199,
                'code': 'CONALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.connectivity_allowance",
            }),
            (0, 0, {
                'name': _('Scale Basic'),
                'sequence': 199,
                'code': 'SCABA',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.scale_basic",
            }),
            (0, 0, {
                'name': _('Personal Allowance'),
                'sequence': 199,
                'code': 'PERALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.Personal_allowance",
            }),
            (0, 0, {
                'name': _('Premium Allowance'),
                'sequence': 199,
                'code': 'PREALW',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.Premium_allowance",
            }),
            (0, 0, {
                'name': _('Relocation Benefit'),
                'sequence': 199,
                'code': 'RELBEN',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.relocation_benefit",
            }),
            (0, 0, {
                'name': _('Repatriation Benefit'),
                'sequence': 199,
                'code': 'REPBEN',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.repatriation_allowance",
            }),
            (0, 0, {
                'name': _('Educational Benefit'),
                'sequence': 199,
                'code': 'EDUBEN',
                'category_id': self.env.ref('hr_payroll.ALW').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': "result = contract.educational_benefit",
            }),
        ])
        return res

    rule_ids = fields.One2many(
        'hr.salary.rule', 'struct_id',
        string='Salary Rules',
        default=_get_default_rule_ids,
        help="Set of salary rules that apply to this structure, automatically loaded with institutional defaults."
    )
