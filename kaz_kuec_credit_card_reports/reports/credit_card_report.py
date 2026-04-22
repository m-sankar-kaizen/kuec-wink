from odoo import models, api


class ReportCreditCard(models.AbstractModel):
    _name = 'report.kaz_kuec_credit_card_reports.credit_card_pdf_template'
    _description = 'Credit Card PDF Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        domain = [
            ('state', '=', 'complete')
        ]

        if data.get('employee_id'):
            domain.append(('requester_emp_id', '=', data['employee_id']))

        if data.get('date_from'):
            domain.append(('order_date', '>=', data['date_from']))

        if data.get('date_to'):
            domain.append(('order_date', '<=', data['date_to']))

        petty_cash_requests = self.env['credit.card.request'].sudo().search(domain)

        return {
            'data': petty_cash_requests,
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to')
        }
