# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError


class ActingAllowance(models.Model):
    """
    Model to manage employee acting allowances in a structured multi-stage approval workflow.

    This model allows an employee to apply for an acting allowance when assuming a different
    job temporarily. The process includes:
    - Department Head Approval
    - HR Approval
    - CEO Approval

    Key Features:
    - Tracks acting job position, justification, and allowance amount
    - Automatically computes allowance based on configured percentage
    - Provides validation for date consistency and contract state
    - Supports renewable acting periods and cron-based auto-finalization
    - Links to employee contracts to prevent overlapping active allowances
    """
    _name = 'employee.acting.allowance'
    _description = "Employee Acting Allowance"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    def get_default_employee(self):
        """
        Get the default employee linked to the current user.

        :return: ID of the employee related to current user
        """
        emp = self.env['hr.employee.public'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return emp.id

    def get_domain(self):

        """Get domain for employees who are subordinates of the current user."""
        employee = self.env['hr.employee.public'].sudo().search([(
            'user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1)
        if employee:
            return [('id', 'in', employee.subordinate_ids.ids)]
        else:
            return []

    employee_id = fields.Many2one('hr.employee.public',
                                  string="Employee",
                                  default=get_default_employee,
                                  domain=get_domain,
                                  help="Employee with grade that has "
                                       "acting allowance enabled.",
                                  required=True,
                                  tracking=True)
    job_id = fields.Many2one(related="employee_id.job_id",
                             help="Job of the employee",
                             string="Employee Job Position")
    acting_job_id = fields.Many2one('hr.job',
                                    required=True,
                                    help="Acting job to which employee is "
                                         "assigned to.",
                                    string="Acting Job Position")
    grade_id = fields.Many2one(related="employee_id.grade_id",
                               help="Grade of the employee.")
    department_id = fields.Many2one(related="employee_id.department_id",
                                    help="Department of the employee.",
                                    string="Department")
    instructions = fields.Text(string="Justifications",
                               help="Details about the acting job position.")
    from_date = fields.Date(string="From Date",
                            required=True,
                            help="Date from which the employee is starting the"
                                 " acting job position.",
                            tracking=True,
                            copy=False,
                            default=lambda self: fields.Date.today())
    to_date = fields.Date(string="To Date",
                          tracking=True,
                          help="Date planned for finalising"
                               " the acting job position.",
                          required=True,
                          default=lambda self: fields.Date.today() + relativedelta(
                              months=3),
                          copy=False)
    is_renewable = fields.Boolean(default=False,
                                  compute="compute_is_renewable")
    state = fields.Selection([('draft', 'Draft'),
                              ('department_head', 'Department Head'),
                              ('hr', 'HR'),
                              ('ceo', 'CEO'),
                              ('approved', 'Running'),
                              ('completed', 'Completed'),
                              ('rejected', 'Rejected'),
                              ('canceled', 'Canceled')],
                             default='draft',
                             tracking=True)
    acting_allowance_percent = fields.Float(
        string='Allowed percentage',
        readonly=True,
        default=10)
    acting_allowance_amount = fields.Monetary(
        string='Allowance amount',
        compute="_compute_allowance_amount",
        currency_field='currency_id',
        help="")
    company_id = fields.Many2one('res.company',
                                 default=lambda
                                     self: self.env.user.company_id.id)
    currency_id = fields.Many2one(related="company_id.currency_id")
    hr_responsible_id = fields.Many2one('res.users', string="Responsible HR",
                                        domain=lambda self: [('groups_id', 'in', [self.env.ref(
                                            'kaz_acting_allowance.group_hr').id,
                                                                                  self.env.ref(
                                                                                      'kaz_acting_allowance.group_ceo').id])])

    @api.constrains('from_date', 'to_date')
    def date_validation(self):
        """
        Validate that the 'to_date' is not earlier than 'from_date'.

        :raises ValidationError: if 'to_date' is before 'from_date'
        """
        for rec in self:
            if rec.to_date < rec.from_date:
                raise ValidationError(
                    _('The to date cannot be earlier than from date.'))

    @api.depends("to_date")
    def compute_is_renewable(self):
        """
        Compute whether the acting allowance is renewable
        based on current date.
        """
        for rec in self:
            if fields.Date.today() >= rec.to_date and rec.state == 'approved':
                rec.is_renewable = True
            else:
                rec.is_renewable = False

    @api.depends('acting_allowance_percent', 'employee_id')
    def _compute_allowance_amount(self):
        """
        Compute the acting allowance amount
         based on the employee's basic salary scale and allowance percent.
        """
        for rec in self:
            if rec.employee_id.sudo().employee_id.contract_id.state == 'open':
                rec.acting_allowance_amount = (
                                                          rec.employee_id.sudo().employee_id.contract_id.scale_basic * rec.acting_allowance_percent) / 100
            else:
                rec.acting_allowance_amount = 0.00

    def action_send_for_department_head_approval(self):
        """
        Move record to 'department_head' state after contract validation.

        :raises ValidationError: if employee has no open contract
        """
        if not self.sudo().employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'department_head'})

    def action_send_for_hr_approval(self):
        """
        Move record to 'hr' state after contract validation.

        :raises ValidationError: if employee has no open contract
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'hr'})

    def action_send_for_ceo_approval(self):
        """
        Move record to 'ceo' state after contract validation.

        :raises ValidationError: if employee has no open contract
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'ceo'})

    def action_approve(self):
        """
        Approve the allowance after validation and update contract link.

        :raises ValidationError: if no open contract or another running allowance exists
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        existing_emp = self.sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('state', 'in', ['approved'])
        ])
        if existing_emp:
            raise ValidationError(_(
                "There's a running allowance for this Employee. "
                "Please change it to any other state."
            ))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = self.id
        self.write({'state': 'approved'})

    def action_reject_department_head(self):
        """
        Reject record from Department Head level.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'rejected'})

    def action_reject_hr(self):
        """
        Reject record from HR level.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'rejected'})

    def action_reject_ceo(self):
        """
        Reject record from CEO level.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'rejected'})

    def action_cancel(self):
        """
        Cancel the allowance.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'canceled'})

    def action_complete(self):
        """
        Mark the allowance as completed.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'completed'})

    def action_reset(self):
        """
        Reset record to draft.
        """
        if self.employee_id.sudo().employee_id.contract_id:
            self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'draft'})

    def action_request_renewal_head(self):
        """
        Request renewal starting with Department Head approval.

        :raises ValidationError: if contract is not open
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'department_head'})

    def action_request_renewal_hr(self):
        """
        Request renewal starting with HR approval.

        :raises ValidationError: if contract is not open
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'hr'})

    def action_request_renewal_ceo(self):
        """
        Request renewal starting with CEO approval.

        :raises ValidationError: if contract is not open
        """
        if not self.employee_id.sudo().employee_id.contract_id.state == 'open':
            raise ValidationError(
                _("The employee doesn't have "
                  "a running contract"))
        self.employee_id.sudo().employee_id.contract_id.acting_allowance_id = ''
        self.write({'state': 'ceo'})

    @api.model
    def _cron_auto_finalise(self):
        """
        Cron job to automatically finalize acting allowances reaching end date.
        Sends reminder on final day and marks complete after one extra day.
        """
        allowances = self.search([])
        for rec in allowances:
            if fields.Date.today() == rec.to_date or fields.Date.today() == rec.to_date + relativedelta(
                    days=1) and rec.state == 'approved':
                base_url = self.env[
                    'ir.config_parameter'].sudo().get_param('web.base.url')
                link = '%s/web#id=%s&view_type=form&action=%s&model=employee.acting.allowance' % (
                    base_url, rec.id, self.env.ref(
                    'kaz_acting_allowance.action_acting_allowance').id)
                mail_template = self.env.ref(
                    'kaz_acting_allowance.email_template_finalise_notify')
                mail_template.with_context({'link': link}).send_mail(
                    rec.id, email_layout_xmlid='mail.mail_notification_light',
                    force_send=True)
            elif fields.Date.today() >= rec.to_date + relativedelta(
                    days=2) and rec.state == 'approved':
                rec.action_complete()

    def unlink(self):
        """
        Prevent deletion unless in 'draft' or 'canceled' state.

        :raises UserError: if trying to delete in any other state
        """
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(
                    _('You cannot delete an acting allowance'
                      ' which is not in draft or cancelled state'))
        return super().unlink()
