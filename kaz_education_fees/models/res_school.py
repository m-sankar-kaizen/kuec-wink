# -*- coding: utf-8 -*-
from odoo import models, fields


class ResSchool(models.Model):
    """
    School Master Model.

    Represents educational institutions that employees' children may attend.
    Used primarily in the Education Fees module to track school details.
    """
    _name = 'res.school'
    _description = 'School'

    name = fields.Char(
        string="School Name",
        required=True,
        help="The official name of the school."
    )

    country_id = fields.Many2one(
        'res.country',
        string="Country",
        default=lambda self: self.env.ref('base.ae'),
        help="The country where the school is located. Defaults to United Arab Emirates."
    )

    state_id = fields.Many2one(
        'res.country.state',
        string="City",
        help="The city or state where the school is located."
    )
