# -*- coding: utf-8 -*-
from odoo import models, api, Command


class HrPayslip(models.Model):
    """Extends hr.payslip to inject loan installment inputs dynamically and manage loan repayment status."""
    _inherit = 'hr.payslip'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides the payslip creation to inject loan installment input lines based on the selected structure.
        Handles country-specific logic for:
        - Saudi KSA National
        - Saudi KSA Expat
        - General (fallback)
        """
        results = super().create(vals_list)
        for result in results:
            if result.employee_id:
                # Retrieve relevant structure IDs
                ksa_struct = self.env.ref(
                    'l10n_sa_hr_payroll.ksa_saudi_employee_payroll_structure').id
                ksa_expat_struct = self.env.ref(
                    'l10n_sa_hr_payroll.ksa_expat_employee_payroll_structure').id
                if result.struct_id.id == ksa_struct:
                    input_id = self.env.ref('ent_ohrms_loan.hr_rule_loan_ksa_saudi').id
                    if input_id:
                        input_type_id = self.env.ref('ent_ohrms_loan.hr_rule_input_loan_ksa_saudi')
                        if input_type_id:
                            if result.struct_id:
                                if result.struct_id.id in input_type_id.struct_ids.ids:
                                    loans = self.env['hr.loan'].search(
                                        [('state', '=', 'approve'),
                                         ('employee_id', '=', result.employee_id.id)])
                                    loan_lines = sum(self.env['hr.loan.line'].search(
                                        [('date', '>=', result.date_from),
                                         ('date', '<=', result.date_to),
                                         ('paid', '=', False),
                                         ('loan_id', 'in', loans.ids)]).mapped('amount'))
                                    total_line = +loan_lines
                                    if loan_lines:
                                        self.env['hr.payslip.input'].create({
                                            'contract_id': result.contract_id.id,
                                            'code': 'LO',
                                            'input_type_id': input_type_id.id,
                                            'payslip_id': result.id,
                                            'amount': total_line,
                                            'name': "Loan of employee"
                                        })
                elif result.struct_id.id == ksa_expat_struct:
                    input_id = self.env.ref('ent_ohrms_loan.hr_rule_loan_ksa_expat').id
                    if input_id:
                        input_type_id = self.env.ref('ent_ohrms_loan.hr_rule_input_loan_ksa_expat')
                        if input_type_id:
                            if result.struct_id:
                                if result.struct_id.id in input_type_id.struct_ids.ids:
                                    loans = self.env['hr.loan'].search(
                                        [('state', '=', 'approve'),
                                         ('employee_id', '=', result.employee_id.id)])
                                    loan_lines = sum(self.env['hr.loan.line'].search(
                                        [('date', '>=', result.date_from),
                                         ('date', '<=', result.date_to),
                                         ('paid', '=', False),
                                         ('loan_id', 'in', loans.ids)]).mapped('amount'))
                                    total_line = +loan_lines
                                    if loan_lines:
                                        self.env['hr.payslip.input'].create({
                                            'contract_id': result.contract_id.id,
                                            'code': 'LO',
                                            'input_type_id': input_type_id.id,
                                            'payslip_id': result.id,
                                            'amount': total_line,
                                            'name': "Loan of employee"
                                        })
                else:
                    input_id = self.env.ref('ent_ohrms_loan.hr_rule_loan_ksa_general').id
                    if input_id:
                        input_type_id = self.env.ref(
                            'ent_ohrms_loan.hr_rule_input_loan_ksa_general')
                        if input_type_id:
                            if result.struct_id:
                                if result.struct_id.id in input_type_id.struct_ids.ids:
                                    loans = self.env['hr.loan'].search(
                                        [('state', '=', 'approve'),
                                         ('employee_id', '=', result.employee_id.id)])
                                    loan_lines = sum(self.env['hr.loan.line'].search(
                                        [('date', '>=', result.date_from),
                                         ('date', '<=', result.date_to),
                                         ('paid', '=', False),
                                         ('loan_id', 'in', loans.ids)]).mapped('amount'))
                                    total_line = +loan_lines
                                    if loan_lines:
                                        self.env['hr.payslip.input'].create({
                                            'contract_id': result.contract_id.id,
                                            'code': 'LO',
                                            'input_type_id': input_type_id.id,
                                            'payslip_id': result.id,
                                            'amount': total_line,
                                            'name': "Loan of employee"
                                        })

        return results

    @api.onchange('struct_id', 'date_from', 'date_to', 'employee_id')
    def onchange_employee_loan(self):
        """
                Onchange handler that injects unpaid loan installment lines into the payslip's input_line_ids.
                Used for interactive UI input detection based on the selected payroll structure and date range.
                """
        for data in self:
            if (not data.employee_id) or (not data.date_from) or (not data.date_to):
                return
            if data.input_line_ids.input_type_id:
                data.input_line_ids = [(5, 0, 0)]
            loan_line = data.struct_id.rule_ids.filtered(
                lambda x: x.code == 'LO')
            # loan_line = self.env.ref('ent_ohrms_loan.hr_rule_input_loan')
            if loan_line:
                get_amount = self.env['hr.loan'].search([
                    ('employee_id', '=', data.employee_id.id),
                    ('state', '=', 'approve')
                ])
                if get_amount:
                    departure_check = (
                            data.employee_id.departure_date and data.date_from <= data.employee_id.departure_date <= data.date_to)
                    for lines in get_amount:
                        for line in lines.loan_lines:
                            if data.date_from <= line.date <= data.date_to or departure_check:
                                if not line.paid:
                                    amount = line.amount
                                    name = loan_line.id
                                    # loan_line.input_id.struct_id = data.struct_id
                                    loan = line.id
                                    self.input_data_line(name, amount, loan)

    def action_payslip_done(self):
        """
        On payslip validation, mark the
        linked loan installments as paid.
        """
        for line in self.input_line_ids:
            if line.loan_line_id:
                line.loan_line_id.paid = True
                line.loan_line_id.loan_id._compute_loan_amount()
        return super().action_payslip_done()

    def action_payslip_cancel(self):
        """
        On payslip cancellation, unmark
        the linked loan installments as paid.
        """
        for line in self.input_line_ids:
            if line.loan_line_id:
                line.loan_line_id.paid = False
                line.loan_line_id.loan_id._compute_loan_amount()
        return super().action_payslip_cancel()

    def input_data_line(self, name, amount, loan):
        for data in self:
            check_lines = []
            new_name = self.env['hr.payslip.input.type'].search([
                ('input_id', '=', name)])
            if new_name:
                line = Command.create({
                    'input_type_id': new_name,
                    'amount': amount,
                    'name': 'LO',
                    'loan_line_id': loan
                })
                check_lines.append(line)
                data.input_line_ids = check_lines
