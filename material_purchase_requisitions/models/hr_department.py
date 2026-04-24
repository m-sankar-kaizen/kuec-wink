# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    """
    Inherits hr.department to introduce stock integration capability by allowing each department
    to optionally define a default destination stock location.

    Use Case:
    - When a department raises a stock request, the system can use `dest_location_id` to prefill
      or route the stock picking to the specified location.
    - Helpful in campus-wide organizations, labs, or departmental warehouses where delivery
      destinations are pre-defined.
    """
    _inherit = 'hr.department'

    dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        help="Default stock destination location for stock moves initiated by this department."
    )
