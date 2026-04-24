# -*- coding: utf-8 -*-
from odoo import models, fields


class AcademicGrade(models.Model):
    """
    Model representing academic or employee grades within an organization.

    Purpose:
        Used to classify employees, students, or other entities
        by academic or job grade level.

    Fields:
        name (Char): The name or label of the grade (e.g., 'Grade A', 'Assistant Professor').

    Notes:
        - This model can be linked with employee records to denote their job level.
        - Extend with additional metadata (e.g., step, scale, salary range) if needed.
    """
    _name = 'academic.grade'
    _description = 'Grade'

    name = fields.Char(string="Grade Name", required=True)
