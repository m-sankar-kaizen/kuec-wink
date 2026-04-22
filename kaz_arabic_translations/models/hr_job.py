# -*- coding: utf-8 -*-
from odoo import models, fields


class HrJob(models.Model):
    """Inherits `hr.job` to store the job position in Arabic."""
    _inherit = 'hr.job'

    employee_arabic_job_position = fields.Char(
        string="Employee Arabic Job Position",
        help="Arabic translation of the job title.")
