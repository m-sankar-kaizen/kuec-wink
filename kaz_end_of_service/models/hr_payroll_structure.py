# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayrollStructure(models.Model):
    """
    Extension of the 'hr.payroll.structure' model to add a flag
    indicating whether a payroll structure is used for end-of-service
    settlements.

    This allows differentiation between regular payroll structures and
    those specifically designed to handle end-of-service calculations,
    such as gratuity, leave encashment, or final settlements.
    """

    _inherit = 'hr.payroll.structure'

    is_end_of_service = fields.Boolean(
        string="End of Service",
        help="Enable this if the payroll structure "
             "is meant for handling end-of-service settlements."
    )
