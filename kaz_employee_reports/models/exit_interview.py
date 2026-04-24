from odoo import models, fields, api


class ExitInterview(models.Model):
    """
        Model: Exit Interview
        ------------------------------------------------------
        This model is used to manage exit interviews for employees leaving the company.
        It captures the reasons for leaving, ratings about the job, department,
        supervisor, organization, benefits received, and suggestions for improvement.

        Key Features:
        - Automatically assigns employee based on the current user.
        - Auto-generates a reference number using sequence.
        - Provides multiple rating and selection fields to capture employee feedback.
        - Handles workflow transitions: draft → waiting approval → approved/rejected/cancelled.
        """
    _name = 'exit.interview'
    _description = "Exit Interview"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_default_employee(self):
        """
                Returns the hr.employee record of the current user, scoped to the current company.
                Used as a default value for the employee name field.
                """
        emp = self.env['hr.employee'].sudo().search(
            [
                ('user_id', '=', self.env.user.id),
                ('company_id', '=', self.env.company.id),
            ])
        return emp.id

    name = fields.Many2one('hr.employee',
                           string='Employee Name',
                           tracking=True,
                           default=get_default_employee)
    ref = fields.Char(readonly=True, default='New')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True,
        tracking=True
    )
    date = fields.Date(string='Date', default=fields.Date.today)
    emp_id = fields.Char(related='name.sequence', string='Employee ID')
    position = fields.Many2one(related='name.job_id' , string='Position')
    department = fields.Many2one(related='name.department_id' , string='Department')
    email = fields.Char(related='name.work_email' , string='Email')
    mobile = fields.Char(related='name.work_phone' , string='Mobile')

    exit = fields.Boolean(string='Raise exit interview on behalf of someone else?')
    further_study = fields.Boolean(string='Further Study')
    conflict = fields.Boolean(string='Conflict with Other Employees')
    family = fields.Boolean(string='Family and/or Personal')
    conflict_with_manager = fields.Boolean(string='Conflict with Managers')
    better_career = fields.Boolean(string='Better Career Opportunity')
    other = fields.Boolean(string='Other ﴾Specify﴿')
    conflict_renewal = fields.Boolean(string='Contract Non‐Renewal')
    circum = fields.Text(string='circumstances')

    # rating
    physical_working_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Physical working environment',
        tracking=True)
    opportunities_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Opportunities for growth and enhancement',
        tracking=True)
    salary_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Salary level and compensation practices',
        tracking=True)
    relation_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Relationship with co‐workers',
        tracking=True)
    direction_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Direction from your Supervisor / Chair')
    support_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Support from your Supervisor / Chair',
        tracking=True)
    quality_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Quality of training and development',
        tracking=True)
    new_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='New employee orientation program',
        tracking=True)
    overall_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Overall satisfaction with the department I worked in',
        tracking=True)
    personal_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Personal job training',
        tracking=True)
    equipment_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Equipment provided ﴾materials, resources, facilities﴿',
        tracking=True)
    performance_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Performance management process',
        tracking=True)
    job_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Overall job satisfaction',
        tracking=True)
    Khalifa_rate = fields.Selection([
        ('high', 'Highly Satisfied'),
        ('satisfied', 'Satisfied'),
        ('dissatisfied', 'Dissatisfied'),
        ('highsatisfied', 'Highly Dissatisfied')
    ], string='Overall satisfaction with Khalifa University as an employer',
    tracking=True)

    # benefits
    salary_level_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Salary Level',
    tracking=True)
    housing_allowance_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Housing Allowance',
    tracking=True)
    ticket_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Tickets/Cash in lieu',
    tracking=True)
    medical_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Medical Plan',
    tracking=True)
    annual_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Annual Vacation',
    tracking=True)
    sick_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Sick Leave',
    tracking=True)
    educational_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Educational Assistance',
    tracking=True)
    relocation_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Relocation Allowance',
    tracking=True)
    repatriation_benefit = fields.Selection([
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('na', 'N / A')
    ], string='Repatriation Allowance',
    tracking=True)

    # Supervisor
    was_consistently_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Was consistently fair',
    tracking=True)
    provided_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Provided recognition',
    tracking=True)
    resolved_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Resolved complaints',
    tracking=True)
    was_sensitive_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Was sensitive to employees’ needs ',
    tracking=True)
    feedback_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Provided feedback on performance',
    tracking=True)
    receptive_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Was receptive to open communication',
    tracking=True)
    encouraged_supervisor = fields.Selection([
        ('almost', 'Almost Always'),
        ('usually', 'Usually'),
        ('sometimes', 'Sometimes'),
        ('never', 'Never')
    ], string='Encouraged initiative and creativity',
    tracking=True)

    #Khalifa University
    advise = fields.Boolean(string='Would you advise a friend to work for The Khalifa University of Science and Technology')
    consider = fields.Boolean(string='Would you consider returning to work at The Khalifa University of Science and Technology')
    experience = fields.Boolean(string='Did your work experience at Khalifa University add value to your knowledge base and/or career path')

    # Regret we are Parting
    most_regret = fields.Text(
        string='In your opinion what did you most enjoy of your employment at The Khalifa University of Science and Technology')
    least_regret = fields.Text(
        string='In your opinion what did you least enjoy of your employment at The Khalifa University of Science and Technology')
    suggestion_regret = fields.Text(
        string='What suggestion do you have to make The Khalifa University of Science and Technology a better place No data found to work')
    general_regret = fields.Text(string='General comments')

    # attachment
    attach = fields.Binary(string='Attach Approved Resignation / '
                                  'Contract Non‐Renewal letter ﴾pdf, jpg only﴿')

    state = fields.Selection(selection=[('draft', 'Draft'),
                                        ('waiting_approval', 'Waiting Approval'),
                                        ('approved', 'Approved'),
                                        ('rejected', 'Rejected'),
                                        ('cancel', 'Canceled'),
                                        ], default='draft', copy=False,
                             tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to auto-generate reference number.
        """
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('exit.interview') or 'New'
        return super().create(vals_list)

    def submit_for_approval(self):
        """Submit the record for managerial approval."""
        self.ensure_one()
        self.write({'state': 'waiting_approval'})

    def approve(self):
        """Approve the exit interview."""
        self.ensure_one()
        self.write({'state': 'approved'})

    def rejected(self):
        """Mark the exit interview as rejected."""
        self.ensure_one()
        self.write({'state': 'rejected'})

    def canceled(self):
        """Cancel the exit interview."""
        self.ensure_one()
        self.write({'state': 'cancel'})

    def reset_to_draft(self):
        """Reset the exit interview to draft state for re-editing."""
        self.ensure_one()
        self.write({'state': 'draft'})
