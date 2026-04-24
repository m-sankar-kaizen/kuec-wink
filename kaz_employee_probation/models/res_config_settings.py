# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    """
    Extension of res.config.settings to allow company-level configuration of
    probation periods via the Settings UI.

    These fields are editable in the settings and stored in the res.company model.
    """
    _inherit = 'res.config.settings'

    period_x_no_of_month_expat = fields.Integer(
        string='Probation Period (Months) for Expat Employees',
        related='company_id.period_x_no_of_month_expat',
        readonly=False,
        help='Default probation period in months for expatriate employees, set at company level.'
    )

    period_x_no_of_month_local = fields.Integer(
        string='Probation Period (Months) for Local Employees',
        related='company_id.period_x_no_of_month_local',
        readonly=False,
        help='Default probation period in months for local employees, set at company level.'
    )
