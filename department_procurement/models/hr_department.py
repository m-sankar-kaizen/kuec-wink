# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrDepartment(models.Model):
    """
    Inherit Department and add
    some fields
    """
    _inherit = 'hr.department'

    @api.depends('name')
    def _compute_short_code(self):
        """Generate short code as the first
        letter of each word in the name."""
        for record in self:
            if record.name:
                record.short_code = ''.join(
                    word[0].upper() for word in record.name.split() if word)
            else:
                record.short_code = ''

    short_code = fields.Char(
        string="Short Code",
        compute="_compute_short_code",
        store=True,
        readonly=False
    )
    planned_item_ids = fields.One2many(
        'annual.department.procurement.plan.items',
        'department_id')
    last_sequence = fields.Integer(default=0)
