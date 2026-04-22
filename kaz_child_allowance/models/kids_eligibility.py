# -*- coding: utf-8 -*-
from odoo import models, fields


class KidsEligibility(models.Model):
    """
    Stores eligibility data for each child in a child allowance request.

    This model links to existing child records and captures their eligibility.
    """
    _name = 'kids.eligibility'
    _description = 'Child Eligibility'

    kids_id = fields.Many2one(
        'kids.details',
        domain="[('parent_id', '=', employee_id)]",
        string="Child"
    )
    age = fields.Date(
        related='kids_id.age',
        readonly=False,
        string="Date of Birth"
    )
    is_eligible = fields.Boolean(
        string="Eligible",
        default=True
    )
    country_id = fields.Many2one('res.country', string="Country of Residence")
    child_allowance_id = fields.Many2one('child.allowance', string="Allowance Request")
    state = fields.Selection(
        related='child_allowance_id.state',
        string="Request Status"
    )
    employee_id = fields.Many2one(
        related='child_allowance_id.employee_id',
        string="Employee"
    )
