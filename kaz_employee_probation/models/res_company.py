# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    """
    Extension of the res.company model to store default probation period settings
    for expatriate and local employees.

    Fields:
    -------
    - period_x_no_of_month_expat: Number of months considered as probation for expats.
    - period_x_no_of_month_local: Number of months considered as probation for locals.
    """
    _inherit = 'res.company'

    period_x_no_of_month_expat = fields.Integer(
        string='Probation Period (Months) for Expat Employees',
        help='Default probation period in months for expatriate employees.'
    )

    period_x_no_of_month_local = fields.Integer(
        string='Probation Period (Months) for Local Employees',
        help='Default probation period in months for local employees.'
    )
