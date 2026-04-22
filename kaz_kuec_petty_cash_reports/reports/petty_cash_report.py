from odoo import models, api


class ReportPettyCash(models.AbstractModel):
    _name = 'report.kaz_kuec_petty_cash_reports.petty_cash_pdf_template'
    _description = 'Petty Cash PDF Report'

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
        petty_cash_journal = self.env.company.default_petty_cash_journal_id
        annual_limit = petty_cash_journal.annual_limit if petty_cash_journal else 0.0
        petty_cash_requests = self.env['petty.cash.request'].sudo().search(domain)

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
            total_unsettled_spend = sum(rec.settlement_ids.filtered(lambda x: x.is_reconciled).mapped('amount'))

            result[emp_id]['total_cash_in'] += amount
            result[emp_id]['transferred_out'] += settled
            result[emp_id]['cash_in_hand'] += unsettled
            result[emp_id]['total_spend_settled'] += total_settled_spend
            result[emp_id]['total_unsettled_spend'] += total_unsettled_spend

        for emp_data in result.values():
            emp_data['remaining_balance'] = (
                    emp_data['annual_limit'] - emp_data['total_cash_in']
            )
        return {
            'data': list(result.values()),
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to')
        }
