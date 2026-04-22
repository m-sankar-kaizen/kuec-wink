# -*- coding: utf-8 -*-
from odoo import models, fields


class HrDepartment(models.Model):
    """Inherits `hr.department` to store the department name in Arabic."""
    _inherit = 'hr.department'

    employee_arabic_department = fields.Char(
        string="Employee Arabic Department",
        help="Arabic translation of the department name.")
