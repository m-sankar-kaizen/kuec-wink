from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    secondment_amount = fields.Monetary(string='Secondment Amount')
    secondment_ids = fields.One2many('hr.employee.secondment',
                                     'payslip_id',
                                     string='Secondments')

    def compute_sheet(self):
        """
        Overrides the standard compute_sheet method to inject the payslip ID
        into the context and compute education allowances before salary computation.
        """
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
            })
            rec.secondment_allowance()
        return super().compute_sheet()

    def secondment_allowance(self):
        id = self.env.context.get('allowance_payslip_id')
        allowance_amt = 0.00
        payslip = self.env['hr.payslip'].browse(id)
        contract = payslip.contract_id
        employee = contract.employee_id
        allowances = self.env['hr.employee.secondment'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'completed'),
            ('allowance_eligible', '=', True),
            ('is_paid', '=', False)
        ])
        percentage = self.env['ir.config_parameter'].sudo().get_param(
            'hr_employee_secondment.allowance_percentage')

        if self.line_ids.filtered(
                lambda x: x.code in [
                    'SECONDMENTALW']):
            allowance_amt = sum(allowances.mapped('total_allowance'))/100 * float(percentage)
        self.write({
            'secondment_amount': allowance_amt
        })

        if self.state == 'paid' and self.line_ids.filtered(
                lambda x: x.code in [
                    'SECONDMENTALW']) and self.env.context.get('unpaid'):
            self.secondment_ids.write({'is_paid': False})

        if self.state == 'done' and self.line_ids.filtered(
                lambda x: x.code in ['SECONDMENTALW']):
            for allowance in allowances:
                if self.env.context.get('paid'):
                    allowance.is_paid = True
                    allowance.payslip_id = self.id

    def action_payslip_paid(self):
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
                'paid': True,
            })
            rec.secondment_allowance()
        return super().action_payslip_paid()

    def action_payslip_unpaid(self):
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
                'unpaid': True,
            })
            rec.secondment_allowance()
        return super().action_payslip_unpaid()

