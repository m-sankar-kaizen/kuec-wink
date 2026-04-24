# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SalaryLetterUAEEXPAT(models.Model):
    """
    Model to manage UAE Expat salary confirmation letters requested by employees.
    This letter may be addressed to external entities (like banks) or issued
    generically ("To Whom It May Concern") for salary or employment verification purposes.

    The model pulls data directly from the logged-in employee's contract, including
    gross salary, job title, and deductions. It also supports addressing the letter
    to predefined entities using the `address.to` model.
    """

    _name = 'salary.letter'
    _description = "Salary Letter"

    def get_default_employee(self):
        """
        Default method to pre-fill the current user's employee record.
        Used to populate the `name` field (employee name).
        """
        emp = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id),
             ('company_id', '=', self.env.company.id)],
            limit=1
        )
        return emp.id

    date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
        help="The date on which the employee requests the salary letter."
    )

    address_type = fields.Selection(
        selection=[
            ('entity', 'Entity'),
            ('whom_ever_it_may_concern', 'To Whom It May Concern')
        ],
        required=True,
        default='entity',
        string='Address Type',
        help="Choose whether to address this "
             "letter to a specific entity (like a bank), "
             "or use a generic 'To Whom It May Concern'."
    )

    letter_id = fields.Many2one(
        'address.to',
        string='Employment Letter Addressed To',
        help="Select the recipient entity to"
             " whom this letter will be addressed."
    )

    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        default=get_default_employee,
        help="The employee requesting the letter. "
             "Automatically filled from login context."
    )

    employee_no = fields.Char(
        related='name.sequence',
        string='Employee No',
        help="The official sequence number or ID of the employee."
    )

    job_title = fields.Many2one(
        related='name.job_id',
        string='Job Title',
        help="The current job title or position of the employee."
    )

    join_date = fields.Date(
        related='name.hire_date',
        string='Joining Date',
        help="The employee's date of joining the organization."
    )

    nationality = fields.Many2one(
        related='name.country_id',
        string='Nationality',
        help="Nationality of the employee, derived from the employee's profile."
    )

    id_no = fields.Char(
        related='name.emirates',
        string='Emirates ID No',
        help="Employee's Emirates ID, pulled from their HR record."
    )

    total_deduction = fields.Float(
        string="Deductions",
        compute='_compute_total_deduction',
        help="Calculated pension-related deductions "
             "(local or Oman) from the employee's contract."
    )

    @api.depends('name')
    def _compute_total_deduction(self):
        """
        Computes total deductions from salary by summing applicable pension deductions.
        Conditions:
        - Local employees: 5% UAE pension.
        - Oman expatriates: 7.5% pension if country is Oman.
        """
        for rec in self:
            if rec.name.sudo().contract_id:
                contract = rec.name.sudo().contract_id
                rec.total_deduction = contract.pension_deduction + contract.pension_deduction_oman
            else:
                rec.total_deduction = 0

    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company.id,
        help="The company issuing the salary letter. "
             "Defaults to the user's company."
    )

    gross_salary = fields.Monetary(
        readonly=True,
        store=True,
        default=lambda x: x.name.sudo().contract_id.total_salary if x.name.sudo().contract_id else 0,
        currency_field='currency_id',
        string='Total Salary',
        help="The total salary amount pulled from "
             "the employee's current contract."
    )

    @api.onchange('name')
    def onchange_name(self):
        """
        Recalculates gross salary when employee is changed.
        Ensures the gross salary is updated even before saving the form.
        """
        self.gross_salary = self.name.sudo().contract_id.total_salary if self.name.sudo().contract_id else 0

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        help="Currency used for salary display. "
             "Pulled from the employee’s company."
    )
