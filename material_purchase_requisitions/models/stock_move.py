# -*- coding: utf-8 -*-
from odoo import models, fields


class StockMove(models.Model):
    """
    Inherits: stock.move

    Adds a connection between stock moves and specific lines of a material requisition.

    This helps track exactly which requested item (and quantity) is being moved, and ensures
    consistency between stock operations and the originating requisition lines.

    Fields:
        - custom_requisition_line_id: Link to the `material.purchase.requisition.line` that triggered this stock move.
    """
    _inherit = 'stock.move'

    custom_requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisitions Line',
        copy=True,
        help="The specific requisition line this stock move fulfills. Enables detailed traceability of internal movements or receipts."
    )
