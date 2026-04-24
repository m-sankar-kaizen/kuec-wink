# -*- coding: utf-8 -*-
from odoo import models, fields


class EmpUnit(models.Model):
    """
    Represents the organizational unit to which employees can be assigned.
    Units may represent major divisions, faculties, or strategic departments
    within the institution or company.

    This model allows HR users to categorize employees based on the high-level
    structural division for reporting and administrative purposes.
    """
    _name = 'employee.unit'
    _description = 'Employee Unit'

    name = fields.Char(
        string='Name',
        required=True,
        help="The name of the organizational unit (e.g., 'Academic Affairs', 'Finance Department')."
    )


class EmpSection(models.Model):
    """
    Represents sub-units or sections within an organizational unit.
    Sections can be used to further refine the employee's organizational placement,
    such as specific departments or working groups under a unit.

    This is useful for more granular reporting or approval routing.
    """
    _name = 'employee.section'
    _description = 'Employee Section'

    name = fields.Char(
        string='Name',
        required=True,
        help="The name of the section under the employee unit (e.g."
             ", 'Accounts Payable', 'Research Coordination')."
    )
