# -*- coding: utf-8 -*-
from odoo import models, fields


class HrContract(models.Model):
    """
    Extension of hr.contract model to link acting allowance details.

    Adds support for tracking the acting allowance assigned to an employee
    through a Many2one relationship with the `employee.acting.allowance` model.
    Also stores the allowance amount as a monetary field.
    """
    _inherit = 'hr.contract'

    acting_allowance_id = fields.Many2one(
        'employee.acting.allowance',
        string="Acting Allowance",
        help="Reference to the current acting allowance record linked to this contract.")

    acting_allowance_amount = fields.Monetary(
        readonly=True,
        help="Calculated acting allowance amount to be paid based on the allowance rules.")
