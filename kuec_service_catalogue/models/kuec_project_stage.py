# -*- coding: utf-8 -*-
from odoo import models, fields


class ProjectTaskTypeWink(models.Model):
    _inherit = 'project.task.type'

    portal_visible = fields.Boolean(
        string='Visible on Customer Portal',
        default=False,
        help="If checked, customers will see this stage in their portal. "
             "Disable for internal-only stages.",
    )
