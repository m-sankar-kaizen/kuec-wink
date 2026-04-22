# -*- coding: utf-8 -*-
from odoo import models, fields


class HrGrade(models.Model):
    """
    Extension of hr.grade model to flag eligibility for acting allowance.

    This boolean field allows configuration of whether employees under a specific grade
    are eligible to receive acting allowances when performing temporary job roles.
    """
    _inherit = 'hr.grade'

    is_allow_acting_allowance = fields.Boolean(
        string="Allow Acting Allowance",
        default=False,
        help="Enable this option if employees in this grade are allowed to receive an acting allowance.")
