# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RegisterForm(models.Model):
    """
    Model representing the employee resignation request (Register Form).

    This model facilitates the process of submitting, reviewing, and approving
    employee resignation forms. It supports an approval workflow with state transitions
    and tracks the leaving reason and resignation metadata.

    Functional Highlights:
    ----------------------
    - Auto-fetch employee based on logged-in user.
    - Auto-generate sequence number for the resignation form.
    - Tracks resignation reasons and dates.
    - Includes standard approval states with tracking.
    - Uses Odoo's chatter and mail activity mixin for logging and communication.
    """

    _name = 'register.form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Resignation Form"

    def get_default_employee(self):
        """
        Returns the current logged-in employee based on user ID and company.
        This is used as the default value for the `name` field.
        """
        emp = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id),
             ('company_id', '=', self.env.company.id)],
            limit=1)
        return emp.id

    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        tracking=True,
        default=get_default_employee,
        help="The employee who is submitting the resignation form."
    )

    ref = fields.Char(
        string='Reference',
        readonly=True,
        default='New',
        help="Auto-generated reference number for this resignation form."
    )

    emp_number = fields.Char(
        related='name.sequence',
        string='Employee Number',
        help="The unique employee sequence number."
    )

    emp_email = fields.Char(
        related='name.work_email',
        string='Email',
        help="Employee's work email address."
    )

    emp_company_id = fields.Many2one(
        related='name.company_id',
        string='Company',
        help="Company associated with the employee."
    )

    reason_id = fields.Many2one(
        'hr.departure.reason',
        tracking=True,
        string='Leaving Reason',
        help="The reason selected by the employee for leaving the organization."
    )

    notify = fields.Date(
        string='Notify On',
        help="The date when the resignation notice is submitted.",
        default=fields.Date.today()
    )

    last_working_date = fields.Date(
        string='Last Working Date',
        help="The employee's final working day in the organization."
    )

    remarks = fields.Char(
        string='Remarks',
        help="Any additional remarks or context provided by the employee."
    )

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
        tracking=True,
        string='Status',
        help="Status of the resignation form in the approval workflow."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to auto-generate reference number.
        """
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('register.form') or 'New'
        return super().create(vals_list)

    def submit_for_approval(self):
        """
        Submits the resignation form for approval by updating its state
        from 'draft' to 'waiting_approval'.
        """
        self.ensure_one()
        self.write({'state': 'waiting_approval'})

    def approve(self):
        """
        Marks the resignation form as approved.
        """
        self.ensure_one()
        self.write({'state': 'approved'})

    def rejected(self):
        """
        Marks the resignation form as rejected.
        """
        self.ensure_one()
        self.write({'state': 'rejected'})

    def canceled(self):
        """
        Cancels the resignation form and resets its state to 'canceled'.
        """
        self.ensure_one()
        self.write({'state': 'cancel'})

    def reset_to_draft(self):
        """
        Resets the resignation form back to the 'draft' state.
        """
        self.ensure_one()
        self.write({'state': 'draft'})
