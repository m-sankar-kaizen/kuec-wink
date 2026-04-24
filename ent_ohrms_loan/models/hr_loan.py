# -*- coding: utf-8 -*-
import calendar

from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class HrLoan(models.Model):
    """
    Model: hr.loan
    Purpose: Manage employee housing advance requests with validation,
    approval workflows, installment planning, and integration into payroll.

    Key Features:
        - Restrict eligibility based on grade-level settings (`is_housing_advance`)
        - Auto-calculate maximum allowable loan based on monthly limit x 12
        - Compute and manage installment lines
        - Handle approval states: draft > submitted > approved > refused/canceled
        - Auto-link loan deductions with payroll via `hr.loan.line` and `hr.payslip`
        - Manage contract validity and probation-based restrictions
        - Allow HR/accounting to approve/refuse requests with audit trail
        - Restrict deletion of loans outside draft/canceled state
    """
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Housing Advance"
    _order = 'id desc'

    # Related contract and grade information
    hire_date = fields.Date(related='employee_id.hire_date')
    over_under = fields.Selection(related='employee_id.is_under_probation',
                                  string='Under Probation')
    employee_contract = fields.Many2one('hr.contract', compute='_compute_employee_contract',
                                        store=True, index=True)
    # Todo: Add store=True, index=True for employee_contract as there is a warning...
    contract_start = fields.Date(related='employee_contract.date_start', string="Contract Start")
    contract_end = fields.Date(related='employee_contract.date_end', string="Contract End")

    grade_id = fields.Many2one(comodel_name='hr.grade', related='employee_id.grade_id',
                               string='Grade')
    is_housing_advance = fields.Boolean(related='grade_id.is_housing_advance')

    attachment = fields.Binary(attachment=True)
    file_name = fields.Char()
    # Fields
    name = fields.Char(string="Housing Advance Seq", default="/", readonly=True)
    date = fields.Date(string="Request Date", default=fields.Date.today())
    employee_id = fields.Many2one('hr.employee', string="Employee", required=True,
                                  domain="[('grade_id.is_housing_advance', '=', True)]")
    department_id = fields.Many2one('hr.department', related="employee_id.department_id",
                                    readonly=True)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", readonly=True,
                                   string="Job Position")

    installment = fields.Selection(
        string="No Of Installments", default='1', required=True,
        selection=[(str(i), str(i)) for i in range(1, 13)])

    payment_date = fields.Date(string="Payment Start Date", required=True,
                               default=fields.Date.today())
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan / Housing Advance Line",
                                 index=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)

    loan_amount = fields.Float(string="Housing Advance Amount", store=True,
                               help="Requested loan amount", tracking=True)

    total_amount = fields.Float(string="Total Amount", compute='_compute_loan_amount')
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_loan_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_loan_amount')
    fully_paid = fields.Boolean('Fully Paid')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', tracking=True, copy=False)

    refuse_reason_ids = fields.One2many('refuse.reason', 'loan_id')

    @api.model_create_multi
    def create(self, vals_list):
        """Assign sequence name to loan if not provided"""
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('/'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.loan.seq') or _('New')
        return super().create(vals_list)

    @api.depends('employee_id')
    def _compute_employee_contract(self):
        """Fetch most recent open contract for employee"""
        for l in self:
            last_contract = self.env['hr.contract'].sudo().search(
                [('employee_id', '=', l.employee_id.id), ('state', '=', 'open')],
                limit=1, order='date_start DESC')
            l.employee_contract = last_contract.id if last_contract else False

    @api.depends('hire_date', 'date')
    def under_probation(self):
        """Compute if employee is under probation (less than 6 months)"""
        for l in self:
            if l.hire_date and l.date:
                months_difference = (l.date.year - l.hire_date.year) * 12 + (
                        l.date.month - l.hire_date.month)
                l.over_under = 'yes' if months_difference < 6 else 'no'
            else:
                l.over_under = 'no'

    @api.model
    def default_get(self, field_list):
        """Auto-assign employee_id based on current user"""
        result = super().default_get(field_list)
        ts_user_id = result.get('user_id') or self.env.context.get('user_id', self.env.user.id)
        result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)],
                                                               limit=1).id
        return result

    @api.depends('loan_lines.paid')
    def _compute_loan_amount(self):
        """Calculate total paid, balance, and mark if fully paid"""
        for loan in self:
            total_paid = sum(line.amount for line in loan.loan_lines if line.paid)
            balance_amount = loan.loan_amount - total_paid
            loan.total_amount = loan.loan_amount
            loan.balance_amount = balance_amount
            loan.total_paid_amount = total_paid
            loan.fully_paid = balance_amount == 0

    @api.constrains('loan_amount')
    def check_loan_amount(self):
        """Ensure loan does not exceed 12 months x per-month allowance"""
        if self.loan_amount > self.grade_id.per_month_housing_advance * 12:
            raise ValidationError(
                _("Maximum loan amount is %d.", self.grade_id.per_month_housing_advance * 12))

    @api.onchange('employee_id')
    def onchange_annual_loan_amount(self):
        """Autofill maximum loan when employee is selected"""
        self.loan_amount = self.grade_id.per_month_housing_advance * 12 if self.grade_id.is_housing_advance else 0

    @api.depends('employee_id')
    def compute_annual_loan_amount(self):
        """Compute max annual loan amount from grade"""
        for rec in self:
            rec.loan_amount = rec.grade_id.per_month_housing_advance * 12 if rec.grade_id.is_housing_advance else 0

    def compute_installment(self):
        """
        Create equal monthly installment lines based on payment date and count.
        Installments align with end-of-month dates.
        """
        for loan in self:
            loan.loan_lines.sudo().unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            month = date_start.month
            year = date_start.year
            last_day = calendar.monthrange(year, month)[1]
            date_start = datetime(year, month, last_day)
            amount = loan.loan_amount / int(loan.installment)
            for i in range(1, int(loan.installment) + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                month = date_start.month + 1
                if month > 12:
                    month = 1
                    year += 1
                last_day = calendar.monthrange(year, month)[1]
                date_start = datetime(year, month, last_day)

            loan._compute_loan_amount()
        return True

    def action_submit(self):
        """Move state to Submitted"""
        self.write({'state': 'waiting_approval_1'})

    def action_cancel(self):
        """Move state to Canceled"""
        self.write({'state': 'cancel'})

    def action_approve(self):
        """Approve loan; only allowed after installments are computed"""
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            data.write({'state': 'approve'})

    def action_refuse(self):
        """Open wizard for refusal reason"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "refuse.reason",
            "context": {
                'default_loan_id': self.id,
                'field_name': 'loan_id',
                'state_field': 'state',
                'state_value': 'refuse',
                'refusal_template_id': 'ent_ohrms_loan.email_template_refusal_notification_hr_loan',
            },
            "name": _("Refuse Reason"),
            "view_mode": "form",
            "target": "new",
        }

    def get_record_url(self):
        """Return full web URL for this loan record"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"

    def unlink(self):
        """Restrict deletion of loans in submitted/approved states"""
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    _('You cannot delete a loan / Housing Advance which is not in draft or cancelled state'))
        return super().unlink()
