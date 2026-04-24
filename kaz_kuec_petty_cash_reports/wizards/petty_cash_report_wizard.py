from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
import json
from odoo.tools import json_default

import io

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class PettyCashReport(models.TransientModel):
    _name = 'petty.cash.report.wizard'
    _description = 'Petty Cash Report Wizard'

    employee_id = fields.Many2one('hr.employee', string='Employees')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for wizard in self:
            if wizard.date_from and wizard.date_to:
                if wizard.date_from > wizard.date_to:
                    raise ValidationError(
                        "Date From must be earlier than or equal to Date To."
                    )

    def _get_petty_cash_report_data(self):
        domain = [
            ('state', '=', 'complete')
        ]

        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        if self.date_from:
            domain.append(('order_date', '>=', self.date_from))

        if self.date_to:
            domain.append(('order_date', '<=', self.date_to))

        petty_cash_journal = self.env.company.default_petty_cash_journal_id
        annual_limit = petty_cash_journal.annual_limit if petty_cash_journal else 0.0
        petty_cash_requests = self.env['petty.cash.request'].sudo().search(
            domain)

        result = {}
        for rec in petty_cash_requests:
            employee = rec.requester_emp_id

            if not employee:
                continue

            emp_id = employee.id

            if emp_id not in result:
                result[emp_id] = {
                    'employee': employee.name,
                    'total_cash_in': 0.0,
                    'transferred_out': 0.0,
                    'cash_in_hand': 0.0,
                    'total_spend_settled': 0.0,
                    'total_unsettled_spend': 0.0,
                    'annual_limit': annual_limit,
                    'remaining_balance': 0.0,
                }
            amount = rec.amount or 0.0
            settled = rec.settlement_amount or 0.0
            total_settled_spend = sum(rec.settlement_ids.filtered(lambda x: x.is_reconciled).mapped('amount'))
            unsettled = rec.different_amount or 0.0
            total_unsettled_spend = sum(rec.settlement_ids.filtered(lambda x: not x.is_reconciled).mapped('amount'))

            result[emp_id]['total_cash_in'] += amount
            result[emp_id]['transferred_out'] += settled
            result[emp_id]['cash_in_hand'] += unsettled
            result[emp_id]['total_spend_settled'] += total_settled_spend
            result[emp_id]['total_unsettled_spend'] += total_unsettled_spend

        for emp_data in result.values():
            emp_data['remaining_balance'] = (
                    emp_data['annual_limit'] - emp_data['total_cash_in']
            )
        return list(result.values())

    def action_print_pdf_report(self):
        self.ensure_one()
        return self.env.ref(
            'kaz_kuec_petty_cash_reports.action_petty_cash_pdf_report'
        ).report_action(
            self,
            data={
                'employee_id': self.employee_id.id or False,
                'date_from': self.date_from,
                'date_to': self.date_to,
            }
        )

    def action_print_xlsx_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_id': self.employee_id.id if self.employee_id else False,
            'today': fields.Date.today(),
        }
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx_petty_cash_report',
            'data': {'model': 'petty.cash.report.wizard',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=json_default),
                     'report_name': 'Petty Cash Report',
                     },
        }

    def get_xlsx_report(self, data, response):
        report_data = self._get_petty_cash_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Petty Cash Report')

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })

        money_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
        })

        text_format = workbook.add_format({
            'border': 1,
        })

        headers = [
            'Requester',
            'Total Cash Transferred In',
            'Total Cash Transferred Out',
            'Cash on Hand',
            'Total Unsettled Spend',
            'Total Spend (Settled)',
            'Annual Limit',
            'Annual Remaining Allowance',
        ]

        row = 0
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
            sheet.set_column(col, col, 22)

        row += 1

        for rec in report_data:
            sheet.write(row, 0, rec['employee'], text_format)
            sheet.write(row, 1, rec['total_cash_in'], money_format)
            sheet.write(row, 2, rec['transferred_out'], money_format)
            sheet.write(row, 3, rec['cash_in_hand'], money_format)
            sheet.write(row, 4, rec['total_spend_settled'], money_format)
            sheet.write(row, 5, rec['total_unsettled_spend'], money_format)
            sheet.write(row, 6, rec['annual_limit'], money_format)
            sheet.write(row, 7, rec['remaining_balance'], money_format)
            row += 1

        workbook.close()
        output.seek(0)

        response.stream.write(output.read())
        output.close()

