# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrJob(models.Model):
    """
    Inherits the core `hr.job` model and extends it with:
    - Job sequence management via a linked model `hr.sequence`
    - Auto-generation of job codes upon creation
    - Conditional publishing logic (enforced delay after creation)
    - Mail notification to company employees when a new job is created
    - Activity support via `mail.activity.mixin`
    """
    _name = 'hr.job'
    _inherit = ['hr.job', 'mail.activity.mixin']

    company_code = fields.Selection(related='company_id.company_code')

    hr_sequence_id = fields.Many2one(
        comodel_name='hr.sequence',
        string='Sequence',
        help="Sequence configuration used to generate job codes."
    )

    def write(self, vals):
        """
        Overrides write method to prevent publishing the job
        before 14 days from creation date.

        Raises:
            ValidationError: If `is_published` is True and 14 days
                             have not passed since the creation date.
        """
        res = super().write(vals)

        if vals.get('is_published') and self.company_code == 'ANK':
            publish_date = self.create_date.date() + relativedelta(days=14)
            if publish_date > fields.Date.today():
                raise ValidationError(
                    f'This job can only be published after {publish_date.strftime("%Y-%m-%d")}.'
                )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to:
        - Generate job codes based on the selected hr.sequence.
        - Queue email notifications to employees of the job's company.
        """
        recs = super().create(vals_list)
        for rec, vals in zip(recs, vals_list):
            rec._assign_job_code(vals)
            rec._notify_company_employees()
        return recs

    def _assign_job_code(self, vals):
        """
        Generates and assigns a job code to this record based on its
        linked hr.sequence.

        The code is composed of the sequence name followed by a zero-padded
        two-digit number representing its position among jobs in that sequence.

        Args:
            vals (dict): The original creation values dict for this record,
                         used to check whether an hr_sequence_id was provided.
        """
        if not vals.get('hr_sequence_id'):
            return

        sequence = self.env['hr.sequence'].browse(vals['hr_sequence_id'])
        job_number = len(sequence.jobs_ids) + 1
        self.job_code = f"{sequence.name}{job_number:02d}"

    def _get_company_employees(self):
        """
        Returns all employees belonging to the same company as this job record.

        Returns:
            hr.employee recordset: Active employees linked to this job's company.
        """
        return self.env['hr.employee'].sudo().search([
            ('company_id', '=', self.company_id.id),
        ])

    def _notify_company_employees(self):
        """
        Queues email notifications to all employees of this job's company.

        Emails are enqueued rather than force-sent to avoid blocking the
        record creation process. Each email is personalised per employee
        using template context variables `link` and `employee`.

        Skips silently if the mail template is not found.
        """
        mail_template = self.env.ref(
            'kaz_recruitment.email_template_new_job',
            raise_if_not_found=False
        )
        if not mail_template:
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        full_url = f"{base_url}{self.website_url or ''}"
        employees = self._get_company_employees()

        for employee in employees:
            mail_template.with_context(
                link=full_url,
                employee=employee,
            ).send_mail(
                self.id,
                email_layout_xmlid='mail.mail_notification_light',
                force_send=False,  # Queued via ir.mail_server cron job
            )