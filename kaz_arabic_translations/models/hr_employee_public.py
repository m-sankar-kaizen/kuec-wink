# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeePublic(models.Model):
    """Public version of `hr.employee` with related Arabic fields."""
    _inherit = 'hr.employee.public'

    employee_arabic_name = fields.Char(
        string="Employee Arabic Name",
        related="employee_id.employee_arabic_name",
        readonly=True)

    employee_arabic_job_position = fields.Char(
        string="Arabic Job Position",
        related="employee_id.employee_arabic_job_position",
        readonly=True)

    employee_arabic_department = fields.Char(
        string="Arabic Department Name",
        related="employee_id.employee_arabic_department",
        readonly=True)

    employee_arabic_nationality = fields.Char(
        string="Employee Arabic Nationality",
        related="employee_id.employee_arabic_nationality",
        readonly=True)
