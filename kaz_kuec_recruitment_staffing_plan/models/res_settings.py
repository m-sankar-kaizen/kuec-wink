from odoo import models, fields
import calendar


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    notify_staffing = fields.Boolean(
        related='company_id.notify_staffing',
        readonly=False)
    recruitment_notification_days = fields.Integer(
        string="X days before calendar year.",
        related='company_id.recruitment_notification_days',
        readonly=False)

    def _cron_notify_procurement_master(self):
        today = fields.Date.today()

        companies = self.search([])
        for rec in companies:
            if rec.notification_day and rec.notification_month:
                departments = self.env['hr.department'].sudo().search([
                    '|', ('company_id', '=', rec.id),
                    ('company_id', '=', False)
                ])
                department_managers = departments.manager_id
                manager_users = department_managers.user_id
                month = int(rec.notification_month)
                day = rec.notification_day
                if today_month == month and today_day == day:
                    group_users = manager_users.filtered(
                        lambda u: u.company_id.id == rec.id)
                    template = self.env.ref(
                        'department_procurement.email_template_procurement_manager_notify')
                    for user in group_users:
                        template.send_mail(user.id, force_send=True)

