# -*- coding: utf-8 -*-
from odoo import models, fields


class AcademicYear(models.Model):
    """
    Model representing an academic year or period.

    Purpose:
        Used to define a specific academic session, such as "2024-2025",
        for use in scheduling, reporting, allowances, or HR eligibility.

    Fields:
        name (Char): A descriptive name for the academic year, e.g., "2024-2025".
        date_start (Date): The start date of the academic year.
        date (Date): The end or expiration date of the academic year.

    Notes:
        - The `date` field is indexed for better search performance.
        - The `date` field is tracked, enabling audit logs for changes.
        - This model can be extended or related to student registration, allowances, contracts, etc.
    """
    _name = 'academic.year'
    _description = 'Year'

    name = fields.Char(string='Academic Year Name', required=True)
    date_start = fields.Date(string='Start Date', required=True)
    date = fields.Date(
        string='Expiration Date',
        index=True,
        required=True,
        help="Date on which this academic year ends."
    )
