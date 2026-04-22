from odoo import models, fields
from odoo.exceptions import ValidationError


class HrLoan(models.Model):
    _inherit = 'hr.loan'

    closing_payslip_id = fields.Many2one('hr.payslip')

    company_code = fields.Selection(related='company_id.company_code')

    def close_loan(self):
        for rec in self:
            structure = self.env.ref('kaz_kuec_housing_loan_closing.housing_adv_settlement_structure')

            payslip = self.env['hr.payslip'].sudo().create({
                'employee_id': rec.employee_id.id,
                'contract_id': rec.employee_contract.id,
                'struct_id': structure.id,
                'housing_loan_closing_id': rec.id,
                'name': 'Housing Advance Closure - ' + rec.employee_id.name
            })
            rec.closing_payslip_id = payslip.id
            payslip.compute_sheet()
            return {
                "type": "ir.actions.act_window",
                "res_model": "hr.payslip",
                "res_id": payslip.id,
                "view_mode": 'form',
                "target": "new",
            }

    def go_to_closing_payslip(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "res_id": self.closing_payslip_id.id,
            "view_mode": 'form',
            "target": "current",
        }

