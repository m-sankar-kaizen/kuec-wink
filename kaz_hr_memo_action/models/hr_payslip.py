from odoo import models, fields
from dateutil.relativedelta import relativedelta


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    disciplinary_deduction_amt = fields.Monetary()

    def compute_sheet(self):
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
            })
            rec.disciplinary_deduction()
        return super().compute_sheet()

    def disciplinary_deduction(self):
        payslip_id = self.env.context.get('allowance_payslip_id')
        deduction_amt = 0.0
        payslip = self.env['hr.payslip'].browse(payslip_id)
        contract = payslip.contract_id
        employee = contract.employee_id
        deductions = self.env['hr.disciplinary.action'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'done'),
            ('action_date', '>=', payslip.date_from),
            ('action_date', '<=', payslip.date_to),
            ('deduction_required', '=', True),
            ('is_deducted', '=', False),
        ])
        for deduction in deductions:
            deduction_amt += deduction.deduction_amount
            if (
                    self.env.context.get('deducted') and
                    payslip.line_ids.filtered(lambda x: x.code == 'DISDED')
            ):
                deduction.write({'paid': True})
        payslip.disciplinary_deduction_amt = deduction_amt
        return deduction_amt

    def action_payslip_paid(self):
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
                'deducted': True,
            })
            rec.child_allowance()
        return super().action_payslip_paid()



