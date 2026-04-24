from odoo import models, fields, api
from datetime import timedelta



class HrContract(models.Model):
    _inherit = 'hr.contract'

    notice_period = fields.Integer(
        string='Notice Period (Days)',
        default=lambda self: self.env.company.employee_notice_period)
    end_date_notify = fields.Integer(
        related='company_id.remind_for_x_days_before_notice_end')

    @api.model
    def notify_contact_end(self):
        contracts = self.search([
            ('company_id.company_code', '=', 'KUEC'),
            ('hr_responsible_id', '!=', False),
        ])
        template = self.env.ref(
            'kaz_kuec_employee_notice_period.email_template_contract_end_notification',
            raise_if_not_found=False
        )
        if not template:
            return

        for contract in contracts:
            if contract.date_end == fields.Date.today() + timedelta(
                    days=contract.end_date_notify) and contract.hr_responsible_id:
                template.send_mail(
                    contract.id,
                    force_send=True
                )
