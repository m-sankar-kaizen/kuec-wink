# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ChildAllowance(models.Model):
    """
    Main model to manage child allowance requests by employees.

    Key Features:
    - Supports default employee and department-based domain filtering
    - Tracks multiple children and supporting documents
    - Enforces validations (e.g., eligibility only for local employees)
    - Manages a multistage approval workflow
    """
    _name = 'child.allowance'
    _description = 'Child Allowance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    def get_default_employee(self):
        """Automatically set the current logged-in user's employee record as default."""
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return emp.id

    def get_default_domain(self):
        """
        Dynamically restrict employee selection based on user's role.

        - If the user is a line manager (but not HR), only show employees in their department.
        - HR can see all employees.
        """
        user = self.env.user
        if user.has_group('kaz_employee_overtime.group_line_manager') \
                and not user.has_group('kaz_employee_overtime.group_hr_person'):
            return [('department_id', '=', user.employee_id.department_id.id)]
        return []

    # Basic fields
    employee_id = fields.Many2one(
        'hr.employee', string="Employee",
        default=get_default_employee,
        domain=get_default_domain,
        required=True, tracking=True
    )
    kaz_employee_type = fields.Selection(
        related='employee_id.kaz_employee_type',
        string="Employee-Type"
    )
    grade_id = fields.Many2one(
        related="employee_id.grade_id",
        string="Grade"
    )
    country_id = fields.Many2one(
        related="employee_id.country_id",
        readonly=False,
        string="Country"
    )
    date = fields.Date(
        string="Request Date",
        default=fields.Date.today
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('line_manager_approval', 'Hr Team'),
        ('hr_approval', 'HR Manager'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled')
    ], default='draft', tracking=True, string="Status")

    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company.id
    )

    # One2many relationship to children records and supporting documents
    kid_ids = fields.One2many(
        'kids.eligibility',
        'child_allowance_id',
        string="Children"
    )
    supporting_document_ids = fields.One2many(
        'supporting.documents',
        'child_allowance_id',
        string="Supporting Documents",
        tracking=True
    )

    paid = fields.Boolean(
        default=False,
        copy=False,
        string="Paid"
    )

    # Constraints and Validations
    @api.constrains('kid_ids', 'supporting_document_ids')
    def _check_kid_ids(self):
        """Ensure at least one eligible child and supporting document are provided."""
        for record in self:
            if not record.kid_ids or not record.supporting_document_ids:
                raise ValidationError(
                    "You must add at least one child's details and a supporting document."
                )

    @api.constrains('employee_id')
    def check_kaz_employee_type(self):
        """Only allow local employees to apply for child allowance."""
        for rec in self:
            if rec.kaz_employee_type != 'local':
                raise UserError(_("Child Allowance is only available for Local Employees."))

    # Workflow actions
    def action_send_for_line_manager_approval(self):
        """Move to Line Manager approval stage."""
        self.write({'state': 'line_manager_approval'})

    def action_send_for_hr_approval(self):
        """Move to HR Manager approval stage."""
        self.write({'state': 'hr_approval'})

    def action_approve(self):
        """Mark request as Approved."""
        self.write({'state': 'approved'})

    def action_reject_line_manager(self):
        """Reject the request at Line Manager level."""
        self.write({'state': 'rejected'})

    def action_reject_hr(self):
        """Reject the request at HR level."""
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """Manually cancel the request."""
        self.write({'state': 'canceled'})

    def reset_draft(self):
        """Reset to draft state for editing."""
        self.write({'state': 'draft'})

    def unlink(self):
        """
        Restrict deletion to only draft or canceled requests.
        Raise an error for other states.
        """
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(
                    _('You cannot delete a child allowance request which is not in draft or cancelled state')
                )
        return super().unlink()



