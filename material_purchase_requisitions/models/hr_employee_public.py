# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeePublic(models.Model):
    """
    Inherits the hr.employee.public model to expose the `dest_location_id` field
    for public (read-only) use where required in portal or public views.

    Note:
    - This field is included only for users in the HR user group, ensuring consistency
      between the full and public employee models in terms of data availability.
    """
    _inherit = 'hr.employee.public'

    dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        groups='hr.group_hr_user',
        help="The default stock destination location assigned to this employee."
    )
