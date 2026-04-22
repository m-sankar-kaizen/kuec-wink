from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class HrGrade(models.Model):
    """
    Represents a Job Grade in the HR system.

    Tracks grade-specific compensation components, responsible users, and grade ranges.
    Includes automation for periodic review alerts (every 3 years).

    Model Inherits:
    ----------------
    - mail.thread: For chatter tracking
    - mail.activity.mixin: For scheduled activities

    Main Fields:
    ------------
    - name: Name of the grade
    - monthly_personal_allowance: Monthly personal allowance amount
    - monthly_premium_uae_allowance: Monthly premium allowance specific to UAE
    - monthly_living_allowance: Monthly living cost allowance
    - monthly_connectivity: Monthly communication/internet allowance
    - social_uae_allowance: Special monthly UAE social allowance
    - minimum_basic, midpoint_basic, maximum_basic: Used to define salary band
    - responsible_user_id: Person in charge of reviewing this grade
    - state: Workflow state of the grade (draft or confirmed)
    - company_id, currency_id: Company context and currency info

    Scheduled Jobs:
    ---------------
    - _cron_grade_review: Notifies responsible users if the grade has not been reviewed in over 3 years
    """
    _name = 'hr.grade'
    _description = "Hr Grade"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Grade Name")
    grade_benefit_id = fields.Many2one('hr.grade.benefit',
                                       string="Grade Benefit")

    monthly_personal_allowance = fields.Float(string='Monthly Personal')
    monthly_premium_uae_allowance = fields.Float(string='Monthly Premium-UAE')
    monthly_living_allowance = fields.Float(string='Monthly Living')
    monthly_connectivity = fields.Float(string='Monthly Connectivity')
    social_uae_allowance = fields.Float(string="Social UAE Allowance")

    minimum_basic = fields.Float(string="Minimum Basic")
    midpoint_basic = fields.Float(string="Midpoint Basic")
    maximum_basic = fields.Float(string="Maximum Basic")

    responsible_user_id = fields.Many2one(
        'res.users',
        string="Responsible User",
        help="User who will be notified when grade needs review"
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company.id
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string="Currency"
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm')
    ], default='draft', tracking=True)

    def action_confirm(self):
        """Set grade status to 'confirm'"""
        for rec in self:
            rec.state = 'confirm'

    def action_reset(self):
        """Reset grade status back to 'draft'"""
        for rec in self:
            rec.state = 'draft'

    @api.model
    def _cron_grade_review(self):
        """
        Automated cron job to identify and notify responsible users
        if any grade has not been reviewed in 3 years since its creation.
        """
        all_grades = self.search([])
        for rec in all_grades:
            if fields.Date.today() >= rec.create_date.date() + relativedelta(
                    years=3):
                base_url = self.env['ir.config_parameter'].sudo().get_param(
                    'web.base.url')
                action_id = self.env.ref('kaz_employees.action_hr_grade').id
                link = f'{base_url}/web#id={rec.id}&view_type=form&action={action_id}&model=hr.grade'
                mail_template = self.env.ref(
                    'kaz_employees.email_template_grade_review')
                mail_template.with_context({'link': link}).send_mail(
                    rec.id,
                    email_layout_xmlid='mail.mail_notification_light',
                    force_send=True
                )
