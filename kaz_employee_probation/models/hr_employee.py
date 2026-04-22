# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    """
    Extension of the hr.employee model to support probation tracking for employees.

    Fields Added:
    -------------
    - is_under_probation: Indicates whether the employee is currently under probation.
    - remaining_days_to_finish_probation: Computed field that shows how many days are left before the probation ends.

    Methods:
    --------
    - compute_remaining_days: Computes the remaining probation days for the employee.
    - check_probation: Cron method to automatically update the probation status based on hire date and company rules.
    """
    _inherit = 'hr.employee'

    company_code = fields.Selection(related='company_id.company_code')

    is_under_probation = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Under Probation")

    remaining_days_to_finish_probation = fields.Integer(
        string="Remaining Days to Finish Probation",
        compute='compute_remaining_days',
        help="Displays the number of days left for probation completion"
    )
    # Fields for extending probation
    is_extend_probation = fields.Boolean(string="Extend Probation", default=False)
    extend_probation_date = fields.Date(string="Extend Probation Date", tracking=True,
                                        help="Date to which the probation is extended")
    extend_probation_remarks = fields.Text(string="Extend Probation Remarks",
                                           tracking=True,
                                           help="Remarks for extending the probation period")

    @api.depends(
        'is_under_probation',
        'kaz_employee_type',
        'hire_date',
        'company_id.period_x_no_of_month_expat',
        'company_id.period_x_no_of_month_local'
    )
    def compute_remaining_days(self):
        """
        Compute the number of days left for the employee to complete their probation period.

        The calculation depends on:
        - Employee type (expat or local),
        - Probation period defined at the company level,
        - Hire date.
        """
        today = fields.Date.context_today(self)
        for employee in self:
            if employee.is_under_probation != 'yes' or not employee.hire_date:
                employee.remaining_days_to_finish_probation = 0
                continue

            # Determine the target probation end date
            if employee.is_extend_probation and employee.extend_probation_date:
                probation_end_date = employee.extend_probation_date
            else:
                probation_months = (
                    employee.company_id.period_x_no_of_month_expat
                    if employee.kaz_employee_type == 'expat'
                    else employee.company_id.period_x_no_of_month_local
                )
                probation_end_date = employee.hire_date + relativedelta(months=probation_months)

            # Compute remaining days
            remaining_days = (probation_end_date - today).days
            employee.remaining_days_to_finish_probation = max(remaining_days, 0)

            # Auto-close probation if period is over
            if remaining_days <= 0:
                employee.is_under_probation = 'no'

    @api.depends('extend_probation_date')
    def _compute_remaining_days(self):
        """
        Compute the remaining days to finish probation based on the
        extended probation date.        """
        today = fields.Date.today()
        for record in self:
            if record.extend_probation_date:
                record.remaining_days_to_finish_probation = (record.extend_probation_date - today).days
            else:
                record.remaining_days_to_finish_probation = 0

    # ============================
    # Validation
    # ============================

    @api.constrains('is_extend_probation', 'extend_probation_date', 'extend_probation_remarks', 'hire_date')
    def _check_probation_extension(self):
        """
        Validation:
        - If 'is_extend_probation' is True, both date and remarks are required.
        - Extended probation cannot exceed 180 days from hire date.
        """
        for rec in self:
            if rec.is_extend_probation:
                if not rec.extend_probation_date or not rec.extend_probation_remarks:
                    raise ValidationError(_("Please fill in Extend Probation Date and Remarks when extending probation."))

                if rec.hire_date and rec.extend_probation_date:
                    delta = (rec.extend_probation_date - rec.hire_date).days
                    if delta > 180:
                        raise ValidationError(_("Extension date cannot be more than 180 days from hire date."))


    @api.model
    def check_probation(self):
        """
        Cron method to update the 'is_under_probation' field.

        Automatically marks employees as not under probation if their hire date
        exceeds the defined probation period for their type (expat/local).
        """
        all_employees = self.search([
            ('hire_date', '!=', False),
            ('is_under_probation', '=', 'yes')
        ])
        today = fields.Date.context_today(self)

        for employee in all_employees:
            # Determine probation duration
            if employee.is_extend_probation and employee.extend_probation_date:
                if employee.extend_probation_date <= today:
                    employee.is_under_probation = 'no'
                continue

            probation_months = 0
            if employee.kaz_employee_type == 'expat':
                probation_months = employee.company_id.period_x_no_of_month_expat
            elif employee.kaz_employee_type == 'local':
                probation_months = employee.company_id.period_x_no_of_month_local

            # Calculate how many full months have passed since hire date
            diff = relativedelta(today, employee.hire_date)
            months_diff = diff.years * 12 + diff.months

            # Mark as no longer under probation if completed
            if months_diff >= probation_months:
                employee.is_under_probation = 'no'


