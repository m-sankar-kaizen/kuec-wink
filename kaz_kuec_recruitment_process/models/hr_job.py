from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError


class HrJob(models.Model):
    _name = 'hr.job'
    _inherit = ['hr.job', 'mail.activity.mixin']


    is_internal_distribution = fields.Boolean()
    is_external_distribution = fields.Boolean()

    company_code = fields.Selection(related='company_id.company_code')

    mode = fields.Selection([
        ('employee', 'By Employee'),
        ('department', 'By Department'),
        ('tag', 'By Tags'),
        ('company', 'By Company'),
    ],
        default="employee")

    mode_employee_ids = fields.Many2many(
        'hr.employee')
    mode_company_id = fields.Many2one('res.company')
    mode_department_id = fields.Many2one('hr.department')
    mode_tag_id = fields.Many2one('hr.employee.category')

    internal_for_specific_duration = fields.Boolean()
    no_of_days = fields.Integer()

    external_mode = fields.Selection([
        ('job_portal', 'Job Portal'),
        ('company_website_external', 'Company Website (External)'),
        ('linkedin', 'Linked In'),
        ('ku', 'KU'),
        ('external_recruitment_companies', 'External Recruitment Companies'),
    ])

    is_job_portal = fields.Boolean(string='Job Portal')
    is_company_website_external = fields.Boolean(string='Company Website (External)')
    is_linkedin = fields.Boolean(string='Linked In')
    is_ku = fields.Boolean(string="KU")
    is_external_recruitment_companies = fields.Boolean(string='External Recruitment Companies')

    kuec_website_url = fields.Char(string="KU Website URL")
    ku_emails = fields.Char(string="KU Emails",
                            help='Comma separated emails')
    ku_partners = fields.Many2many('res.partner',
                                   string="KU Partners")

    salary_min = fields.Monetary(currency_field='company_currency_id')
    salary_max = fields.Monetary(currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency',
                                          related='company_id.currency_id')

    def publish_on_website(self):
        self.write({
            'is_published': True,
            'website_published': True
        })

    def unpublish_on_website(self):
        self.write({
            'is_published': False,
            'website_published': False
        })

    def notify_external(self):
        template = self.env.ref(
            'kaz_kuec_recruitment_process.mail_template_external_recruitment_request',
            raise_if_not_found=False
        )
        if not template:
            raise UserError("Email template not found.")
        for job in self:
            if not job.ku_partners:
                continue
            for rec in job.ku_partners:
                template.sudo().with_context(partner_email=rec.email).send_mail(
                    job.id, force_send=True)

    def notify_employees(self):
        """Dispatch notifications based on the selected mode."""
        self.ensure_one()
        users = self._get_users_by_mode()
        self._create_activity_for_users(users)

    def _get_users_by_mode(self):
        """Return a recordset of users depending on the selected mode."""
        self.ensure_one()
        if self.mode == 'employee':
            return self.mode_employee_ids.user_id
        if self.mode == 'department':
            return self.mode_department_id.member_ids.user_id
        if self.mode == 'tag':
            employees = self.env['hr.employee'].sudo().search([
                ('category_ids', 'in', [self.mode_tag_id.id])
            ])
            return employees.user_id
        if self.mode == 'company':
            employees = self.env['hr.employee'].sudo().search([
                ('company_id', '=', self.mode_company_id.id)
            ])
            return employees.user_id
        return self.env['res.users']

    def _create_activity_for_users(self, users):
        """
        Create mail.activity for each user passed.
        :param users: recordset of res.users
        """
        for user in users:
            self.env['mail.activity'].sudo().create({
                'summary': f'Internal Job Posted: {self.name}.',
                'activity_type_id': self.env.ref(
                    'mail.mail_activity_data_todo').id,
                'res_model_id': self.env['ir.model']._get_id('hr.job'),
                'res_id': self.id,
                'user_id': user.id,
            })

    @api.model
    def _cron_auto_external(self):
        Job = self.env['hr.job'].sudo()

        internal_jobs = Job.sudo().search([
            ('is_internal_distribution', '=', True),
            ('internal_for_specific_duration', '=', True),
        ])
        for rec in internal_jobs:
            expiry_date = rec.create_date.date() + timedelta(
                days=rec.no_of_days)

            if fields.Date.today() >= expiry_date:
                rec.is_published = True
                rec.is_external_distribution = True


class WebsitePublishedMixin(models.AbstractModel):
    _inherit = "website.published.mixin"

    website_published = fields.Boolean(readonly=True)

    is_published = fields.Boolean(readonly=True)



