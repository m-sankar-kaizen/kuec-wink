from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    company_code = fields.Selection(
        related='company_id.company_code')

    employee_bank_id = fields.Many2one(
        'res.bank',
        compute='_compute_employee_bank_id',
        store=True,
        string='Bank')

    @api.depends(
        'employee_id',
    )
    def _compute_employee_bank_id(self):
        for rec in self:
            rec.employee_bank_id = False
            if rec.employee_id.bank_name_id:
                rec.employee_bank_id = rec.employee_id.bank_name_id.id

    def action_print_payslip_kuec(self):
        report_name = 'kaz_kuec_fields.kuec_customized_payslip_report'
        bank_transfer_history = self.employee_id.bank_transfer_history_ids
        data = {'bank_transfer_history': False}
        bank_transfer_approved = bank_transfer_history.filtered(lambda r: r.state == 'approved')
        bank_transfer_in_date = bank_transfer_approved.filtered(
            lambda r: r.transfer_date and self.date_from <= r.transfer_date <= self.date_to)
        if bank_transfer_in_date:
            data['bank_transfer_history'] = bank_transfer_in_date
        return self.env.ref(report_name).report_action(self)
