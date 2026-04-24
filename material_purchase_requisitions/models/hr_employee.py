# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    """
    Inherits the hr.employee model to introduce a new field `dest_location_id` for specifying
    a default stock destination location per employee.

    Use Case:
    - Useful in scenarios where materials or assets are assigned directly to employees and
      should be delivered to a designated stock location (e.g., employee's desk, lab, office).
    - This can be used in integration with internal transfer or requisition workflows.
    - Field is visible only to HR users.

    Security:
    - The field is restricted to users with 'Human Resources / Officer' access (group_hr_user).
    """
    _inherit = 'hr.employee'

    dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        groups='hr.group_hr_user',
        help="The default stock destination location assigned to this employee."
    )
