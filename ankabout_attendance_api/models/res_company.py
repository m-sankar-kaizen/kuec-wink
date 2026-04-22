# -*- coding: utf-8 -*-
from odoo import models, fields


class Company(models.Model):
    """
    Extends the res.company model to include attendance integration features.

    Fields:
        attendance_token (Char): A token used to authenticate external attendance systems
                                 when syncing data with Odoo's HR Attendance module.
    """
    _inherit = 'res.company'

    ############################# Attendance Integration #############################
    attendance_token = fields.Char(
        string='Attendance Token',
        help='Authentication token for external attendance integration systems.'
    )
