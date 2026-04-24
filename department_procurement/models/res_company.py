from odoo import models, fields, api
import calendar
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    notification_month = fields.Selection(
        [(str(i), calendar.month_name[i]) for i in range(1, 13)],
        string="Notification Month"
    )
    notification_day = fields.Integer(string="Notification Day")

    @api.constrains("notification_month", "notification_day")
    def _check_valid_day(self):
        for rec in self:
            if rec.notification_month and rec.notification_day:
                month = int(rec.notification_month)
                max_day = calendar.monthrange(2000, month)[1]
                if rec.notification_day < 1 or rec.notification_day > max_day:
                    raise ValidationError(
                        f"Invalid day for {calendar.month_name[month]}. "
                        f"Allowed range: 1–{max_day}."
                    )

    def _cron_notify_procurement_master(self):
        today = fields.Date.today()
        today_month = today.month
        today_day = today.day
        companies = self.search([])
        for rec in companies:
            if rec.notification_day and rec.notification_month:
                departments = self.env['hr.department'].sudo().search([
                    '|', ('company_id', '=', rec.id),
                    ('company_id', '=', False)
                ])
                department_managers = departments.manager_id
                group_users = department_managers.user_id
                month = int(rec.notification_month)
                day = rec.notification_day
                if today_month == month and today_day == day:
                    template = self.env.ref(
                        'department_procurement.email_template_procurement_manager_notify')
                    for user in group_users:
                        template.send_mail(user.id, force_send=True)
