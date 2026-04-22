# -*- coding: utf-8 -*-
from odoo import models, fields


class HrAssignmentCategory(models.Model):
    """
    Model to represent categories of assignments for HR contracts.

    Used to classify employees' roles into categories like:
    Academic, Administrative, Research, Technical, etc.

    Fields:
        name (Char): Name of the assignment category.
    """
    _name = 'hr.assignment.category'
    _description = 'HR Assignment Category'

    name = fields.Char(
        string="Category Name",
        required=True,
        help="Descriptive name of the assignment category."
    )
