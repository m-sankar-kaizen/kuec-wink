# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.addons.hr_payroll.models.hr_payslip import HrPayslip as Payslip


class HrContract(models.Model):
    """
    Extension of hr.payslip to include fields and methods for handling
    child education allowance components (book, transport, tuition, and other fees).
    """
    _inherit = 'hr.payslip'

    education_fees = fields.Float('Education Fees')
    book_fees = fields.Float()
    transportation_fees = fields.Float()
    tuition_fees = fields.Float()
    other_fees = fields.Float()
    refund_payslip_id = fields.Many2one('hr.payslip', string='Refund Payslip')

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
            rec.child_education_allowance()
        return super().compute_sheet()

    def child_education_allowance(self):
        """
        Calculates total child education allowance components from confirmed
        education fee records for the employee for the same year as the payslip.

        It sums the book, transport, tuition, and other fees, and sets them on the payslip.
        If the payslip is finalized and includes all 4 allowance components, the related
        education.fees records are marked as paid (unless it's a credit note).

        :return: Total allowance amount (currently unused, placeholder for extensibility).
        :rtype: float
        """
        id = self.env.context.get('allowance_payslip_id')
        allowance_amt = 0.00
        payslip = self.env['hr.payslip'].browse(id)
        contract = payslip.contract_id
        employee = contract.employee_id
        allowances = self.env['education.fees'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'confirmed'),
            ('year', '=', payslip.date_from.year)
        ])

        for field in ['book_fees', 'transportation_fees', 'tuition_fees', 'other_fees']:
            self.write({
                field: sum(allowances.filtered(lambda rec: not rec.paid and not rec.payslip_id).mapped(field))
            })

        if self.state == 'done' and len(self.line_ids.filtered(
                lambda x: x.code in ['CHILDALWBOOK', 'CHILDALWTRANSPORT', 'CHILDALWTUITION', 'CHILDALWOTHERFEES'])) == 4:
            for allowance in allowances:
                if not self.credit_note and not allowance.paid:
                    allowance.paid = True
                    allowance.payslip_id = self.id
                else:
                    if allowance.payslip_id.id == self.refund_payslip_id.id:
                        allowance.paid = False
                        allowance.payslip_id = False

        return allowance_amt

    def action_payslip_paid(self):
        """
        Ensures education allowance components are updated when the payslip is marked as paid.

        Also sets related education.fees records as paid if applicable.
        """
        for rec in self:
            rec.env.context = dict(rec.env.context)
            rec.env.context.update({
                'allowance_payslip_id': rec.id,
                'paid': True,
            })
            rec.child_education_allowance()
        return super().action_payslip_paid()


def refund_sheet(self):
    copied_payslips = self.env['hr.payslip']
    for payslip in self:
        copied_payslip = payslip.copy({
            'credit_note': True,
            'name': _('Refund: %(payslip)s', payslip=payslip.name),
            'edited': True,
            'state': 'verify',
            'refund_payslip_id': payslip.id,
        })
        for wd in copied_payslip.worked_days_line_ids:
            wd.number_of_hours = -wd.number_of_hours
            wd.number_of_days = -wd.number_of_days
            wd.amount = -wd.amount
        for line in copied_payslip.line_ids:
            line.amount = -line.amount
            line.total = -line.total
        copied_payslips |= copied_payslip
    formview_ref = self.env.ref('hr_payroll.view_hr_payslip_form', False)
    treeview_ref = self.env.ref('hr_payroll.view_hr_payslip_tree', False)
    return {
        'name': ("Refund Payslip"),
        'view_mode': 'list, form',
        'view_id': False,
        'res_model': 'hr.payslip',
        'type': 'ir.actions.act_window',
        'target': 'current',
        'domain': [('id', 'in', copied_payslips.ids)],
        'views': [(treeview_ref and treeview_ref.id or False, 'list'),
                  (formview_ref and formview_ref.id or False, 'form')],
        'context': {}
    }


Payslip.refund_sheet = refund_sheet
