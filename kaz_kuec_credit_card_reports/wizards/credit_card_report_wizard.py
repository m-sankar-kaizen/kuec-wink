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


class CreditCardReport(models.TransientModel):
    _name = 'credit.card.report.wizard'
    _description = 'Credit Card Report Wizard'

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

        credit_cash_requests = self.env['credit.card.request'].sudo().search(
            domain)

        return credit_cash_requests

    def action_print_pdf_report(self):
        self.ensure_one()
        return self.env.ref(
            'kaz_kuec_credit_card_reports.action_credit_card_pdf_report'
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
            'report_type': 'xlsx_credit_card_report',
            'data': {'model': 'credit.card.report.wizard',
                     'output_format': 'xlsx',
                     'options': json.dumps(data,
                                           default=json_default),
                     'report_name': 'Credit Card Report',
                     },
        }

    def get_xlsx_report(self, data, response):
        report_data = self._get_petty_cash_report_data()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Credit Card Report')

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
            'From : To',
            'Credit Card / Number',
            'Holder',
            'Total Spent',
            'Settled Amount',
            'Unsettled Spent',
            'Credit card limit',
        ]

        row = 0
        for col, header in enumerate(headers):
            sheet.write(row, col, header, header_format)
            sheet.set_column(col, col, 22)

        row += 1

        for rec in report_data:
            sheet.write(
                row,
                0,
                f"{str(rec.approve_date or '')} to {str(rec.card_return_date or '')}",
                text_format
            )
            sheet.write(row, 1, rec.journal_id.credit_card, money_format)
            sheet.write(row, 2, rec.requester_emp_id.name, money_format)
            sheet.write(row, 3, rec.amount, money_format)
            sheet.write(row, 4, sum(rec.settlement_ids.filtered(lambda x: x.is_reconciled).mapped('amount')), money_format)
            sheet.write(row, 5, sum(rec.settlement_ids.filtered(lambda x: not x.is_reconciled).mapped('amount')), money_format)
            sheet.write(row, 6, rec.journal_id.maximum_credit_card, money_format)
            row += 1

        workbook.close()
        output.seek(0)

        response.stream.write(output.read())
        output.close()

