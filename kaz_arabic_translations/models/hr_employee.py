# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    """Inherits `hr.employee` to add Arabic information fields."""
    _inherit = 'hr.employee'

    employee_arabic_name = fields.Char(
        string="Employee Arabic Name",
        help="Employee name written in Arabic.")

    employee_arabic_job_position = fields.Char(
        related="job_id.employee_arabic_job_position",
        string="Arabic Job Position",
        help="Job position title in Arabic, related from job record.")

    employee_arabic_department = fields.Char(
        related="department_id.employee_arabic_department",
        string="Arabic Department Name",
        help="Department name in Arabic, related from department record.")

    employee_arabic_nationality = fields.Char(
        string="Employee Arabic Nationality",
        compute="compute_arabic_nationality",
        store=False,
        help="Nationality translated to Arabic based on country_id.")

    @api.depends('country_id')
    def compute_arabic_nationality(self):
        """
        Compute Arabic name for the nationality by activating Arabic language context.
        """
        for rec in self:
            rec.employee_arabic_nationality = rec.country_id.with_context(lang='ar_001').name
