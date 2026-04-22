from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    housing_loan_closing_id = fields.Many2one(
        comodel_name='hr.loan',
        string='Housing Loan Closing',
        help='Link to the housing loan '
             'closing record associated with this payslip.'
    )

    def action_payslip_paid(self):
        res = super().action_payslip_paid()
        if self.housing_loan_closing_id:
            self.housing_loan_closing_id.write({'fully_paid': 'true'})
        return res


