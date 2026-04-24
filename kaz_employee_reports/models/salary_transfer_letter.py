# -*- coding: utf-8 -*-
from odoo import models, fields


class SalaryTransferLetter(models.Model):
    """
    Model to manage salary transfer letter requests, typically issued by an employee
    to the employer requesting a formal letter to a bank confirming salary deposit details.

    This model collects key employment and personal information from the HR records,
    including job title, salary, joining date, and nationality, and links it to the
    employee’s preferred bank (via `res.bank`). Useful for formal documentation
    related to salary account verification and loan processing.
    """

    _name = 'salary.transfer.letter'
    _description = "Salary Transfer Letter"

    def get_default_employee(self):
        """
        Returns the current logged-in employee, based on the user and company context.
        Used to prefill the `name` (employee) field when the form is opened.
        """
        emp = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id),
             ('company_id', '=', self.env.company.id)])
        return emp.id

    date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        help="The date on which the salary transfer letter request is made."
    )

    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        default=get_default_employee,
        help="The employee requesting the salary transfer letter."
    )

    bank_id = fields.Many2one(
        'res.bank',
        related='name.bank_name_id',
        string='Bank Name',
        help="The bank where the employee wants the salary to be transferred. "
             "Fetched from the employee’s profile."
    )

    employee_no = fields.Char(
        related='name.sequence',
        string='Employee No',
        help="Employee ID or sequence number from the HR record."
    )

    job_title = fields.Many2one(
        related='name.job_id',
        string='Job Title',
        help="The employee’s current job title or position."
    )

    join_date = fields.Date(
        related='name.hire_date',
        string='Joining Date',
        help="The date on which the employee joined the company."
    )

    nationality = fields.Many2one(
        related='name.country_id',
        string='Nationality',
        help="Nationality of the employee, based on HR record."
    )

    id_no = fields.Char(
        related='name.emirates',
        string='Emirates ID No',
        help="Emirates ID number of the employee, pulled from the employee record."
    )

    gross_salary = fields.Monetary(
        related='name.contract_id.total_salary',
        currency_field='currency_id',
        string='Total Salary',
        help="Total gross salary of the employee, as per the current contract. "
             "Used for salary confirmation in the transfer letter."
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help="Currency in which the salary is paid. Taken from the company record."
    )

    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company,
        help="Company issuing the letter. Set to the current user’s company."
    )


