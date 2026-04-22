# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class BankDetails(models.Model):
    """
    Main model for employee bank transfer requests.

    Tracks the employee’s current and new bank details, manages state transitions
    through approvals, and ensures required validations are enforced.
    """
    _name = 'bank.transfer'
    _description = 'Bank Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Name',
        readonly=True,
        copy=False,
        default=lambda self: _('New'),
        help="Unique identifier for the bank transfer request (auto-generated)."
    )

    # Utility methods to fetch defaults from hr.employee
    def get_default_employee(self):
        """Return current user's linked employee record."""
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return emp.id if emp else []

    def get_default_bank(self):
        """Return employee's current bank."""
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return emp.bank_name_id.id if emp and emp.bank_name_id else []

    def get_default_branch(self):
        """Return employee's current bank branch."""
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return emp.bank_branch_id.id if emp and emp.bank_branch_id else []

    # def get_default_iban(self):
    #     """Return employee's current IBAN."""
    #     emp = self.env['hr.employee'].sudo().search([
    #         ('user_id', '=', self.env.user.id),
    #         ('company_id', '=', self.env.company.id)
    #     ], limit=1)
    #     return emp.bank_name_id.iban_num if emp and emp.bank_name_id else ''

    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        default=get_default_employee,
        required=True,
        tracking=True,
        help="Employee requesting the bank transfer."
    )
    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company.id,
        help="Company to which the employee belongs."
    )

    transfer_date = fields.Date(string='Transfer Date')

    @api.onchange('employee_id')
    def get_employee_details(self):
        """Autofill current bank details when employee is changed."""
        self.current_bank_id = self.employee_id.bank_name_id.id
        self.branch_id = self.employee_id.bank_branch_id.id
        self.iban_no = self.employee_id.iban_num

    current_bank_id = fields.Many2one(
        'res.bank',
        string="Current Bank",
        default=get_default_bank,
        tracking=True,
        copy=False,
        help="The employee's current registered bank."
    )
    branch_id = fields.Many2one(
        'bank.branch',
        string="Branch",
        copy=False,
        default=get_default_branch,
        tracking=True,
        help="Current branch of the employee's bank."
    )
    iban_no = fields.Char(
        string="IBAN No.",
        tracking=True,
        help="Current IBAN registered for the employee."
    )

    # New requested details
    new_bank_id = fields.Many2one(
        'res.bank',
        string="New Bank",
        required=True,
        tracking=True,
        help="New bank requested for the transfer."
    )
    new_branch_id = fields.Many2one(
        'bank.branch',
        string="New Branch",
        required=True,
        tracking=True,
        help="New bank branch requested."
    )
    new_iban_no = fields.Char(
        string="New IBAN No.",
        required=True,
        readonly=False,
        tracking=True,
        help="New IBAN number. Must start with 'AE' and have 21 digits."
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_approval', 'HR Team'),
        ('director_approval', 'Payroll Officer'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled')
    ],
        default='draft',
        copy=False,
        tracking=True,
        help="State of the bank transfer request."
    )

    supporting_document_ids = fields.One2many(
        'bank.support.documents',
        'transfer_id',
        help="Required documents supporting the bank transfer request."
    )

    @api.onchange('new_iban_no')
    def _onchange_iban(self):
        """Ensure IBAN starts with 'AE' on input."""
        for rec in self:
            if rec.new_iban_no and not rec.new_iban_no.startswith('AE'):
                rec.new_iban_no = f"AE{rec.new_iban_no}"

    @api.constrains('new_iban_no')
    def _check_iban_format(self):
        """
        Check that IBAN follows UAE format:
        - Starts with 'AE'
        - Total length = 23 characters
        - Remaining 21 characters must be digits
        """
        for rec in self:
            if (
                not rec.new_iban_no
                or not rec.new_iban_no.startswith('AE')
                or len(rec.new_iban_no) != 23
                or not rec.new_iban_no[2:].isdigit()
            ):
                raise ValidationError(
                    "IBAN must start with 'AE' followed by exactly 21 digits.")

    @api.constrains('supporting_document_ids')
    def check_supporting_documents(self):
        """Ensure at least one document is attached."""
        for record in self:
            if not record.supporting_document_ids:
                raise ValidationError("Please add supporting documents.")

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate name using sequence if not provided."""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'bank.transfer') or _('New')
        return super().create(vals_list)

    def send_notify2_group(self, group_xml_id):
        """
        Send a scheduled activity to all users in the specified group.

        :param group_xml_id: XML ID of the group (e.g. 'module_name.group_xyz')
        """
        users = self.env.ref(group_xml_id).users
        for user in users:
            self.activity_schedule(
                act_type_xmlid='kaz_bank_transfer.mail_activity_send_note2_approve',
                note='Please Approve',
                user_id=user.id
            )

    def action_send_for_hr_approval(self):
        """Move request to HR approval stage and notify HR group."""
        self.send_notify2_group('kaz_bank_transfer.group_hr_person')
        self.write({'state': 'hr_approval'})

    def action_send_for_director_approval(self):
        """Move request to Director (Payroll) approval stage and notify Director group."""
        self.send_notify2_group('kaz_bank_transfer.group_director')
        self.write({'state': 'director_approval'})

    def action_approve(self):
        """Approve request and update employee's official bank details."""
        self.employee_id.bank_name_id = self.new_bank_id.id
        self.employee_id.bank_branch_id = self.new_branch_id.id
        self.employee_id.iban_num = self.new_iban_no
        self.transfer_date = fields.Date.today()
        self.write({'state': 'approved'})

    def action_reject_hr(self):
        """Reject request from HR stage."""
        self.write({'state': 'rejected'})

    def action_reject_director(self):
        """Reject request from Director (Payroll) stage."""
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """Manually cancel the request."""
        self.write({'state': 'canceled'})

    def unlink(self):
        """Only allow deletion when in draft or canceled state."""
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(
                    _("You cannot delete a bank transfer request"
                      " that isn't in Draft or Canceled state."))
        return super().unlink()
