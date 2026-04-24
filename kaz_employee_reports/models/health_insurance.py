# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HealthInsurance(models.Model):
    """
    Model: Health Insurance Request

    This model handles the internal workflow for employees of an organization to
    request various health insurance-related changes or actions.

    Supported request types:
    - Self-enrollment
    - Status change (e.g., marital status)
    - Addition of family members (e.g., spouse, children)
    - Newborn baby addition
    - Coverage for dependents over 18
    - Policy cancellation (with/without a Certificate of Coverage letter)

    Key features:
    - Auto-fill personal information for the logged-in employee
    - Approval workflow including HR and HR manager
    - Tracks submission states and prevents deletions of approved entries
    - Allows attachment of supporting documents (e.g., passport copy)
    """

    _name = 'health.insurance'
    _description = 'Health Insurance'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_default_employee(self):
        """
        Returns the employee record ID linked to the currently logged-in user.

        :return: ID of hr.employee record
        :rtype: int
        """
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1)
        return emp.id

    name = fields.Many2one('hr.employee',
                           string='Employee',
                           default=get_default_employee)
    ref = fields.Char(readonly=True, default='New')
    date = fields.Date(string='Date', default=fields.Date.today)
    emp_id = fields.Char(related='name.sequence', string='Employee ID')
    position = fields.Many2one(related='name.job_id', string='Position')
    department = fields.Many2one(related='name.department_id', string='Department')
    email = fields.Char(related='name.work_email', string='Email')
    mobile = fields.Char(related='name.work_phone', string='Mobile')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 readonly=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_approve', 'HR Team'),
        ('hr_manager', 'HR Manager'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancel')],
        default='draft',
        tracking=True)

    is_behalf_of_someone_else = fields.Boolean(
        default=False,
        tracking=True,
        string='Submitted on behalf of someone else?'
    )

    # Personal Information Fields
    full_name = fields.Char(string='Full Name')
    father_name = fields.Char(string="Father's Name")
    marital_status = fields.Selection(related='name.marital',
                                      compute_sudo=True,
                                      groups="base.group_user",
                                      string='Marital Status')
    contact_no = fields.Char('Contact No')
    email_id = fields.Char(string='Email ID')
    nationality = fields.Many2one('res.country', string='Nationality')
    passport_num = fields.Char(string='Passport No')
    date_of_birth = fields.Date(string='Date Of Birth')

    type_of_request = fields.Selection([
        ('self', 'Self'),
        ('status_change', 'Status Change'),
        ('family_member', 'Family Member'),
        ('new_born_baby', 'New Born Baby'),
        ('dependent_over_18', 'Dependent Over 18'),
        ('cancellation_with_coc_letter', 'Cancellation with COC Letter'),
        ('cancellation_without_coc_letter', 'Cancellation without COC Letter'),
    ], string='Type of Request', default='self')

    # Department / Family Data
    num_of_children = fields.Integer(string='No Of Children',
                                     groups="base.group_user",
                                     compute_sudo=True,
                                     related='name.children')
    children_age = fields.Char(string='Children Age',
                               compute_sudo=True,
                               groups="base.group_user",
                               compute='calc_children_age')
    spouse_name = fields.Char(string='Spouse Name',
                              compute_sudo=True,
                              groups="base.group_user",
                              related='name.spouse_complete_name')

    # Attachment Section
    attach = fields.Binary(string='Attachment File')
    attachment_name = fields.Char(string='File Name')

    def send_notify2_group(self, group_xml_id):
        """
        Schedules an approval activity for all users in the given security group.

        :param group_xml_id: The external ID of the security group (e.g., 'base.group_hr_user')
        :type group_xml_id: str
        """
        users = self.env.ref(group_xml_id).users
        if users:
            for user in users:
                self.activity_schedule(
                    act_type_xmlid='kaz_employee_reports.mail_activity_send_note2_approve',
                    note='Please Approve',
                    user_id=user.id)


    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create method to auto-generate reference number.
        """
        for vals in vals_list:
            vals['ref'] = self.env['ir.sequence'].next_by_code('health.insurance') or 'New'
        return super().create(vals_list)

    def action_send_for_hr_approval(self):
        """
        Moves the request to the HR approval stage and notifies HR group.
        """
        self.send_notify2_group('kaz_employee_reports.group_hr_person')
        self.write({'state': 'hr_approve'})

    def action_send_for_hr_manager_approval(self):
        """
        Sends the request to the HR Manager for final approval.
        """
        self.send_notify2_group('kaz_employee_reports.hr_manager')
        self.write({'state': 'hr_manager'})

    def action_approve(self):
        """
        Marks the request as fully approved.
        """
        self.write({'state': 'approved'})

    def action_reject(self):
        """
        Marks the request as rejected.
        """
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """
        Cancels the request.
        """
        self.write({'state': 'cancel'})

    def unlink(self):
        """
        Prevents deletion of records unless they are in draft or canceled state.

        :raises UserError: If trying to delete a record in any other state.
        """
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(
                    _('You cannot delete a health insurance '
                      'request which is not in draft or cancelled state'))
        return super().unlink()

    @api.onchange('type_of_request', 'name')
    def _onchange_type_and_name(self):
        """
        Auto-fills personal data if request type is 'self'.
        Clears the fields otherwise.
        """
        for rec in self:
            employee = rec.name.sudo()
            is_employee = rec.type_of_request == 'self'
            rec.full_name = employee.name if is_employee else ""
            rec.father_name = employee.father_name if is_employee else ""
            rec.email_id = employee.work_email if is_employee else ""
            rec.date_of_birth = employee.birthday if is_employee else ""
            rec.contact_no = employee.mobile_phone if is_employee else ""
            rec.nationality = employee.country_id if is_employee else ""
            rec.passport_num = employee.passport_id if is_employee else ""

    @api.depends('name')
    def calc_children_age(self):
        """
        Computes and displays a comma-separated string of children's ages
        by accessing the employee's `kid_ids` and their calculated ages.
        """
        for rec in self:
            rec.children_age = ", ".join(map(str, rec.name.kid_ids.mapped('age_calc')))


