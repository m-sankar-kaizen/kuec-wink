# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ExitClearance(models.Model):
    """
    Model to handle the Employee Exit Clearance process.

    This form captures various departments' inputs such as:
    - Communication (Email, Mobile)
    - HR (Personal info)
    - IT (Equipment and accounts)
    - EHSS (Facility clearance)
    - Research services

    The form supports a workflow with states like Draft, Waiting Approval,
    Approved, Rejected, and Cancelled.
    """
    _name = 'exit.clearance'
    _description = "Exit Clearance"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_default_employee(self):
        """
        Return the default employee associated with the current user.
        """
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1)
        return emp.id

    # Employee requesting the clearance
    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        tracking=True,
        default=get_default_employee
    )

    # Unique reference, auto-generated via sequence
    ref = fields.Char(
        readonly=True,
        default='New'
    )

    # Company related to the request
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True
    )
    # Metadata
    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        tracking=True
    )

    emp_id = fields.Char(
        related='name.sequence',
        string='Employee ID'
    )
    position = fields.Many2one(
        related='name.job_id',
        string='Position'
    )
    department = fields.Many2one(
        related='name.department_id',
        string='Department'
    )
    email = fields.Char(
        related='name.work_email',
        string='Email'
    )
    mobile = fields.Char(
        related='name.work_phone',
        string='Mobile'
    )

    # Proxy exit option
    exit = fields.Boolean(
        string='Raise exit interview on behalf of someone else?'
    )

    # Communication details
    communication_email = fields.Char(string='Email')
    communication_Mobile = fields.Char(string='Mobile')

    # HR personal information
    personal_telephone = fields.Char(string='Personal Mobile')
    personal_email = fields.Char(string='Personal Email')
    personal_address = fields.Char(string='Personal Address')

    # Passport details
    passport_name = fields.Char(string='Full Name as per Passport')
    passport_date = fields.Date(string='Date of Birth')

    # IT department section
    email_it = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='I would like to request email forwarding'
    )
    equipment_it = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='I would like to keep IT equipment (Laptop, Hard Drive etc) till my last day of work'
    )
    request_it = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='Have you ever requested generic IT accounts (e.g. Ask@ku.ac.ae) that are no longer required?'
    )

    # EHSS section
    ehss_facilites = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='I would like to keep EHSS materials till my last day of work'
    )

    # Research Services section
    principle_service = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='Are you a Principal Investigator / Co‐Investigator on an active research project?'
    )
    responsible_service = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='Are you supervising research staff or students assigned to projects?'
    )
    research_service = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='Are you a research staff member working on project(s)?'
    )

    # Confirmation fields
    confirm_data = fields.Boolean(string='I confirm that the information provided is accurate')
    attach = fields.Binary(string='Attachment (if any)')

    # Workflow state
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('waiting_approval', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancel', 'Canceled'),
        ],
        default='draft',
        copy=False,
        tracking=True
    )


    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to auto-generate reference number.
        """
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('exit.clearance') or 'New'
        return super().create(vals_list)


    # State transition methods
    def submit_for_approval(self):
        """Move record to 'waiting_approval' state."""
        self.ensure_one()
        self.write({'state': 'waiting_approval'})

    def approve(self):
        """Approve the clearance request."""
        self.ensure_one()
        self.write({'state': 'approved'})

    def rejected(self):
        """Reject the clearance request."""
        self.ensure_one()
        self.write({'state': 'rejected'})

    def canceled(self):
        """Cancel the clearance request."""
        self.ensure_one()
        self.write({'state': 'cancel'})

    def reset_to_draft(self):
        """Reset the record to draft state."""
        self.ensure_one()
        self.write({'state': 'draft'})
