# -*- coding: utf-8 -*-
from odoo import models, fields


class EmploymentLetter(models.Model):
    """
    Model to manage Employment Letter requests made by employees.

    This model supports two address types:
        1. To a specific entity (e.g., bank, embassy).
        2. A general "To Whom It May Concern" type letter.

    Fields like job title, joining date, nationality, etc. are auto-fetched from the employee profile.
    """
    _name = 'employment.letter'
    _description = "Employment Letter"

    def get_default_employee(self):
        """
        Automatically fetch the employee record linked to the current user.

        Returns:
            int: The ID of the employee record if found, else None.
        """
        emp = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id),
             ('company_id', '=', self.env.company.id)],
            limit=1
        )
        return emp.id

    # Date the letter is requested
    date = fields.Date(
        string='Request Date',
        default=fields.Date.today
    )

    # Determines the type of letter address (to an entity or generic)
    address_type = fields.Selection(
        selection=[
            ('entity', 'Entity'),
            ('whom_ever_it_may_concern', 'To Whom It May Concern')
        ],
        required=True,
        default='entity'
    )

    # Reference to a predefined address or recipient entity
    letter_id = fields.Many2one(
        'address.to',
        string='Employment Letter Address To'
    )

    # The employee requesting the letter (auto-filled from logged-in user)
    name = fields.Many2one(
        'hr.employee',
        string='Employee Name',
        default=get_default_employee
    )

    # Employee sequence number (read-only)
    employee_no = fields.Char(
        related='name.sequence',
        string='Employee No',
        readonly=True
    )

    # Job title from employee record (read-only)
    job_title = fields.Many2one(
        related='name.job_id',
        string='Job Title',
        readonly=True
    )

    # Joining date from employee record (read-only)
    join_date = fields.Date(
        related='name.hire_date',
        string='Joining Date',
        readonly=True
    )

    # Nationality (country) from employee record (read-only)
    nationality = fields.Many2one(
        related='name.country_id',
        string='Nationality',
        readonly=True
    )

    # Emirates ID from employee record (read-only)
    id_no = fields.Char(
        related='name.emirates',
        string='Emirates ID No',
        readonly=True
    )

    # Company associated with the letter (defaults to logged-in user's company)
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company.id,
        readonly=True
    )
    # location fields added due to the approval mechanism
    country_id = fields.Many2one(
        'res.country',
        string="Country",
        required=True,
        default=lambda self: self.env.ref('base.ae'),
        help="The country of the recipient, useful for international correspondence."
    )
    state_id = fields.Many2one(
        'res.country.state',
        string="Location",
        required=True,
        domain="[('country_id.code', '=', 'AE')]",
        help="The state of the recipient, useful for international correspondence.",
        default=lambda self: self.env['res.country.state'].search(
            [('name', '=', 'Abu Dhabi'), ('country_id.code', '=', 'AE')], limit=1)
    )
