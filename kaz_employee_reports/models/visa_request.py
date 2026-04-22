# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VisaRequest(models.Model):
    """
    Model representing visa-related requests by employees, such as employment visa,
    residence visa for family, or visit visa applications.

    Supports a multi-stage approval workflow:
        - Draft → HR Team → HR Manager → Approved/Rejected
        - Tracks visa type, action type, and personal details pulled from the employee profile
        - Can be raised by an employee or on behalf of another employee
    """

    _name = 'visa.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Visa Request'

    def get_default_employee(self):
        """
        Automatically fetches the current employee record of the logged-in user,
        used to pre-fill the `name` field.
        """
        return self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1).id

    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        default=get_default_employee,
        help="The employee submitting the visa request."
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True,
        help="Company from which the visa request is submitted."
    )

    ref = fields.Char(
        string="Reference",
        readonly=True,
        default='New',
        help="Unique reference number automatically generated on creation."
    )

    date = fields.Date(
        string='Date',
        default=fields.Date.today,
        help="Date on which the visa request is made."
    )

    emp_id = fields.Char(
        related='name.sequence',
        string='Employee ID',
        help="System-generated employee sequence number."
    )

    type_of_request = fields.Selection([
        ('employment', 'Employment Visa'),
        ('residence', 'Residence Visa For Family Member'),
        ('transfer', 'Transfer Visa'),
        ('single', 'Single Visit Visa 90 Days'),
        ('one', 'One Way Travel Visa 14 Days')],
        string='Type Of Request',
        default='employment',
        help="Specifies the kind of visa the employee is requesting."
    )

    type_of_action = fields.Selection([
        ('new', 'New Visa'),
        ('renewal', 'Visa Renewal'),
        ('transfer', 'Transfer Visa'),
        ('correction', 'Correction'),
        ('visa', 'Visa Cancellation')],
        string='Type Of Action',
        default='new',
        help="Type of operation to be performed on the visa."
    )

    marital_status = fields.Selection(
        related='name.marital',
        compute_sudo=True,
        groups="base.group_user",
        string="Marital Status",
        help="Marital status from the employee record."
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_approve', 'HR Team'),
        ('hr_manager', 'HR Manager'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancel')],
        default='draft',
        tracking=True,
        help="Workflow state of the visa request."
    )

    spouse_complete_name = fields.Char(
        related='name.spouse_complete_name',
        compute_sudo=True,
        groups="base.group_user",
        string="Spouse Name",
        help="Full name of the employee's spouse."
    )

    spouse_employee_id = fields.Many2one(
        related='name.spouse_employee_id',
        compute_sudo=True,
        groups="base.group_user",
        string="Spouse Employee",
        help="Spouse employee record if also in the system."
    )

    children = fields.Text(
        compute="_compute_children",
        compute_sudo=True,
        groups="base.group_user",
        string="Children",
        help="Comma-separated list of employee's children."
    )

    check = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')],
        string='Raised on behalf of another?',
        help="Indicates whether this request is made on behalf of someone else."
    )

    # Personal Info
    full_name = fields.Char(string='Full Name')
    father_name = fields.Char(string='Father’s Name')
    mother_name = fields.Char(string='Mother’s Name')
    position = fields.Char(string='Applicant’s Position')
    religion = fields.Char(string='Religion')
    sect = fields.Char(string='Sect')
    country_num = fields.Char(string='Contact Number (Home Country)')
    uae_num = fields.Char(string='Contact Number (UAE)')
    personal_email = fields.Char(string='Personal Email Address')
    po_box = fields.Char(string='PO Box')
    nationality = fields.Many2one('res.country', string='Nationality')
    passport_num = fields.Char(string='Passport Number')
    passport_country = fields.Many2one('res.country', string='Passport Issued Country')
    passport_expired_date = fields.Date(string='Passport Expiry Date')
    country_live_in = fields.Many2one('res.country', string='Currently Living In')
    country_of_birth = fields.Many2one('res.country', string='Country of Birth')
    place_of_birth = fields.Char(string='Place of Birth')
    education_qualify = fields.Char(string='Education Qualification')
    major = fields.Char(string='Major')
    comment = fields.Text(string='Additional Comments')
    attach = fields.Binary(string='Attachment File')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to auto-generate reference number.
        """
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('visa.request') or 'New'
        return super().create(vals_list)

    @api.depends('name')
    def _compute_children(self):
        """
        Computes a comma-separated
        string of child names associated with the employee.
        """
        for rec in self:
            rec.children = ", ".join(
                [child.name for child in rec.name.kid_ids]) if rec.name.kid_ids else ""

    @api.onchange('type_of_request', 'name')
    def _onchange_type_and_name(self):
        """
        Auto-populates personal fields from
        employee record when type_of_request = 'employment'.
        Clears data otherwise.
        """
        for rec in self:
            employee = rec.name.sudo()
            is_self_request = rec.type_of_request == 'employment'

            rec.full_name = employee.name if is_self_request else ""
            rec.father_name = employee.father_name if is_self_request else ""
            rec.mother_name = employee.mother_name if is_self_request else ""
            rec.position = employee.job_id.name if is_self_request else ""
            rec.uae_num = employee.phone if is_self_request else ""
            rec.personal_email = employee.private_email if is_self_request else ""
            rec.nationality = employee.country_id if is_self_request else ""
            rec.passport_num = employee.passport_id if is_self_request else ""
            rec.country_of_birth = employee.country_of_birth if is_self_request else ""
            rec.place_of_birth = employee.place_of_birth if is_self_request else ""
            rec.passport_expired_date = employee.passport_expiration if is_self_request else ""

    def send_notify2_group(self, group_xml_id):
        """
        Sends a scheduled activity
        notification to all users in the given group.

        :param group_xml_id: The XML ID of the user group to notify.
        """
        users = self.env.ref(group_xml_id).users
        for user in users:
            self.activity_schedule(
                act_type_xmlid='kaz_employee_reports.mail_activity_send_note2_approve',
                note='Please Approve',
                user_id=user.id
            )

    def action_send_for_hr_approval(self):
        """Transitions request to HR team for first-level approval."""
        self.send_notify2_group('kaz_employee_reports.group_hr_team_visa_request')
        self.write({'state': 'hr_approve'})

    def action_send_for_hr_manager_approval(self):
        """Transitions request to HR Manager for final-level approval."""
        self.send_notify2_group('kaz_employee_reports.group_hr_manager_visa_request')
        self.write({'state': 'hr_manager'})

    def action_approve(self):
        """Marks request as approved."""
        self.write({'state': 'approved'})

    def action_reject(self):
        """Marks request as rejected."""
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """Cancels the request."""
        self.write({'state': 'canceled'})

    def unlink(self):
        """
        Restricts deletion to
        requests in 'draft' or 'canceled' state only.
        """
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(_(
                    'You cannot delete a Visa Request '
                    'that is not in draft or canceled state.'))
        return super().unlink()
