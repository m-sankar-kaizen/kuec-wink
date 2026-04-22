# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    """
    Extend res.partner to flag whether a partner is an employee.
    Useful for filtering or linking to HR-related modules.
    """
    _inherit = 'res.partner'

    is_employee = fields.Boolean(string='Is Employee')  # Flag for identifying employee partners
