
from odoo import fields, models


class HrEmployeeRelation(models.Model):
    """Model to store employee relationship information."""

    _name = 'hr.employee.relation'
    _description = 'HR Employee Relation'

    name = fields.Char(string="Relationship",
                       help="Relationship with the employee")
