from odoo import models, fields
from datetime import timedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    probation_period_days = fields.Integer(
        string='Probation Period (Days)',
        default=90,
        help='X number of days to be probation period of any new comers in KUEC.'
    )
    remind_for_x_days_before_probation_end = fields.Integer(
        string='Remind X Days Before Probation End',
        store=True,
        default=7,
        help='Number of days before the probation end date to send a reminder.'
    )

    maximum_probation_extension_period = fields.Integer(
        string='Maximum Probation Extension Period (Days)',
        default=30,
        help='Maximum number of days to which the probation period can be extended.'
    )

    def _cron_notify_employee_probation(self):
        """
        Cron job to notify HR Managers about employees
        whose probation is ending soon.
        """

        today = fields.Date.today()

        companies = self.search([
            ('company_code', '=', 'KUEC'),
            ('remind_for_x_days_before_probation_end', '>', 0),
        ])

        hr_users = self.env.ref('hr.group_hr_manager').users.filtered(
            lambda u: u.email
        )

        for company in companies:
            reminder_days = company.remind_for_x_days_before_probation_end
            target_date = today + timedelta(days=reminder_days)
            employees = self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('probation_end_date', '=', target_date),
            ])

            if not employees:
                continue
            table_rows = ""
            for emp in employees:
                table_rows += f"""
                    <tr>
                        <td>{emp.name}</td>
                        <td>{emp.job_title or ''}</td>
                        <td>{emp.department_id.name or ''}</td>
                        <td>{emp.probation_end_date}</td>
                    </tr>
                """

            table_html = f"""
                <table border="1" cellpadding="5" cellspacing="0" width="100%">
                    <thead>
                        <tr>
                            <th>Employee Name</th>
                            <th>Job Title</th>
                            <th>Department</th>
                            <th>Probation End Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            """
            body_html = f"""
                <p>Dear HR Team,</p>

                <p>
                    The following employees are approaching the end of their probation period
                    in <strong>{company.name}</strong>.
                </p>

                {table_html}

                <p>
                    Please take the necessary action.
                </p>

                <p>Regards,<br/>
                </p>
            """

            for user in hr_users:
                mail_values = {
                    'subject': 'Employees Probation Ending Soon',
                    'email_from': company.email or self.env.user.company_id.email,
                    'email_to': user.email,
                    'body_html': body_html,
                    'auto_delete': True,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()


