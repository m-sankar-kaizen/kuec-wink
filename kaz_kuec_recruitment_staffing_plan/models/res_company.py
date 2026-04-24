from odoo import models, fields, api
from datetime import timedelta, date
import calendar
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    notify_staffing = fields.Boolean()
    recruitment_notification_days = fields.Integer(
        string="X days before calendar year.")

    def _cron_notify_staffing_plan(self):
        today = fields.Date.today()
        current_year = today.year
        dec_31 = date(current_year, 12, 31)
        companies = self.search([
            ('notify_staffing', '=', True)])

        for rec in companies:
            notify_date = dec_31 - timedelta(
                days=rec.recruitment_notification_days)
            if today == notify_date:
                departments = self.env['hr.department'].sudo().search([
                    '|', ('company_id', '=', rec.id),
                    ('company_id', '=', False)
                ])
                for department in departments:
                    department_manager = department.manager_id
                    manager_user = department_manager.user_id
                    template = self.env.ref(
                        'kaz_kuec_recruitment_staffing_plan.email_template_department_manager_notify')
                    context = {
                        'department': department.name,
                    }
                    template.with_context(context).send_mail(manager_user.id,
                                                             force_send=True)
