# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class EmployeePromotion(models.Model):
    """This model is necessary for add employee promotion details in employee
       module """
    _name = 'employee.promotion'
    _description = 'Employee Promotion'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True
    _order = 'id desc'

    name = fields.Char(required=True, string='Name', help='Promotion name')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    contract_id = fields.Many2one('hr.contract', string='Contract',
                                  help='Contract of employee')
    job_title_id = fields.Many2one('hr.job',
                                   string='Old Designation',
                                   help='Previous job of employee ')
    job_salary = fields.Monetary(string='Previous Salary',
                                 required=True, help='Previous job salary',
                                 currency_field='currency_id')
    promotion_date = fields.Date(string='Promotion Date',
                                 default=fields.Date.today(),
                                 help='Date of promotion date')
    promotion_type_id = fields.Many2one('promotion.type',
                                        string='Promotion Type',
                                        required=True,
                                        help='Promotion type of promotion')
    new_designation_id = fields.Many2one('hr.job',
                                         string='New Designation',
                                         required=True,
                                         help='New designation of employee')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    new_salary = fields.Monetary(string='New Salary', required=True, help='New salary',
                                 currency_field='currency_id')
    description = fields.Text(string='Description', help='Description of the promotion')

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending', 'In Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft'
    )

    def action_submit(self):
        """Submit for approval"""
        if self.state != 'draft':
            raise ValidationError(_("Only draft records can be submitted."))
        self._check_existing_promotion_request()
        self.state = 'pending'

    def action_approve(self):
        """Approve the record"""
        if self.state != 'pending':
            raise ValidationError(_("Only records in approval can be approved."))
        self.state = 'approved'

    def action_reject(self):
        """Reject the record"""
        if self.state != 'pending':
            raise ValidationError(_("Only records in approval can be rejected."))
        self.state = 'rejected'

    def action_cancel(self):
        """Cancel the record"""
        if self.state in ['approved', 'rejected', 'cancelled']:
            raise ValidationError(_("Cannot cancel an already processed record."))
        self.state = 'cancelled'

    def action_reset_to_draft(self):
        """Reset the record"""
        if self.state not in ['rejected', 'cancelled']:
            raise ValidationError(_("Cannot Reset a record which is not canceled or rejected."))
        self.state = 'draft'

    def action_promote(self):
        # TODO add this functionality
        ...

    @api.constrains('employee_id')
    def _check_existing_promotion_request(self):
        for rec in self:
            if not rec.employee_id:
                continue
            existing = self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', 'in', ['draft', 'pending']),
                ('id', '!=', rec.id)  # exclude the current record
            ])
            if existing:
                raise ValidationError(
                    _("Employee %s already has a promotion request in draft or pending state.") %
                    rec.employee_id.name
                )

    @api.constrains('employee_id', 'new_salary')
    def _check_salary(self):
        for rec in self:
            if rec.job_salary >= rec.new_salary:
                raise UserError("New Salary is less than the employee's Current salary")

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.job_title_id = self.employee_id.job_id.id
        self.contract_id = self.employee_id.contract_id.id
        self.job_salary = self.employee_id.contract_id.wage
